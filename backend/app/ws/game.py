"""/ws/game — the online-play socket. Contract in docs/ARCHITECTURE.md §5."""

import asyncio
from typing import Any

import chess
import jwt as pyjwt
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import get_session_factory
from app.models import RatingMode, User
from app.services import coach as coach_service
from app.services import games as game_service
from app.services import matchmaking
from app.services.elo import get_or_create_rating
from app.services.games import LiveGame, MoveError
from app.telemetry import writer
from app.ws.manager import game_manager as manager

log = structlog.get_logger()
router = APIRouter()


async def _authenticate(ws: WebSocket) -> int | None:
    token = ws.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token)
    except pyjwt.InvalidTokenError:
        return None
    if payload.get("type") != "access":
        return None
    return int(payload["sub"])


async def on_game_over(game: LiveGame, payload: dict[str, Any]) -> None:
    """Shared with the REST layer (bot-game creation passes it as on_over)."""
    await manager.send_room(game.id, {"type": "game:over", "data": payload})
    await _award_game_xp(game, payload["result"])
    manager.drop_room(game.id)


async def _award_game_xp(game: LiveGame, result: str) -> None:
    """Grant XP to the human player(s). Online rates both humans; Bot Arena the
    human; Learn games (coached practice) grant none."""
    from app.models import GameMode
    from app.services import gamification

    if game.mode == GameMode.LEARN or result == "ABORTED":
        return

    def event_for(color: str) -> str:
        if result == "DRAW":
            return "game_draw"
        won = (result == "WHITE" and color == "w") or (result == "BLACK" and color == "b")
        return "game_win" if won else "game_loss"

    humans: list[tuple[int, str]] = []
    if game.white_id is not None:
        humans.append((game.white_id, "w"))
    if game.black_id is not None:
        humans.append((game.black_id, "b"))

    async with get_session_factory()() as db:
        for uid, color in humans:
            summary = await gamification.on_event(db, uid, event_for(color), ref=str(game.id))
            await manager.send_user(uid, {"type": "xp:update", "data": summary})


async def _drive_bot(game: LiveGame) -> None:
    async def notify(payload: dict[str, Any]) -> None:
        await manager.send_room(game.id, {"type": "game:move", "data": payload})

    await game_service.drive_bot(game, notify)
    if game.coach_level is not None and game.status == "active":
        await _coach_after_move(game, moved_by="b")


def _coach_budgets(game: LiveGame) -> tuple[int | None, int | None]:
    cfg = coach_service.COACH_LEVELS[game.coach_level or 1]
    hints = cfg["hints"]
    takebacks = cfg["takebacks"]
    hints_left = None if hints is None else max(0, hints - game.hints_used)
    tb_left = None if takebacks is None else max(0, takebacks - game.takebacks_used)
    return hints_left, tb_left


async def _coach_after_move(game: LiveGame, moved_by: str) -> None:
    """Evaluate the fresh position and push level-filtered info to the human.
    LEARN games always have the human as white."""
    if game.coach_level is None or game.white_id is None:
        return
    fen = game.board.fen()
    ply = len(game.moves)
    prev = game.last_eval_cp
    cp = await coach_service.evaluate(fen)
    if cp is None:
        return
    game.last_eval_cp = cp
    drop = None
    if moved_by == "w" and prev is not None:
        drop = coach_service.win_pct(prev) - coach_service.win_pct(cp)
    hints_left, tb_left = _coach_budgets(game)
    info = coach_service.build_info(
        game.coach_level,
        ply=ply,
        eval_cp=cp,
        drop=drop,
        hints_left=hints_left,
        takebacks_left=tb_left,
    )
    # The client keeps the human's move verdict on screen until their next move;
    # a "b" refresh only updates the eval bar and must not wipe what's being read.
    info["moved_by"] = moved_by
    await manager.send_user(game.white_id, {"type": "coach:info", "data": info})


async def _start_game(
    a_id: int, b_id: int, base_min: float | None, inc_sec: int, rated: bool
) -> None:
    # Queue order decides color: first-in plays white.
    game = await game_service.create_game(
        white_id=a_id,
        black_id=b_id,
        rated=rated,
        base_min=base_min,
        inc_sec=inc_sec,
        on_over=on_game_over,
    )
    manager.join_room(game.id, a_id)
    manager.join_room(game.id, b_id)

    async with get_session_factory()() as db:
        users = {
            u.id: u for u in (await db.scalars(select(User).where(User.id.in_([a_id, b_id])))).all()
        }
        ratings = {
            uid: (await get_or_create_rating(db, uid, RatingMode.ONLINE)).value
            for uid in (a_id, b_id)
        }
        await db.commit()

    for uid, color in ((a_id, "w"), (b_id, "b")):
        opp = users[b_id if uid == a_id else a_id]
        await manager.send_user(
            uid,
            {
                "type": "queue:matched",
                "data": {
                    "game_id": game.id,
                    "color": color,
                    "opponent": {
                        "username": opp.username,
                        "rating": ratings[opp.id],
                    },
                },
            },
        )
    await manager.send_room(game.id, {"type": "game:state", "data": game.state_payload()})


async def _handle(user_id: int, msg: dict[str, Any]) -> dict[str, Any] | None:
    """Returns an error payload to send back, or None."""
    mtype = msg.get("type")
    data = msg.get("data") or {}

    if mtype == "queue:join":
        tc = data.get("time_control") or {}
        base_min = tc.get("base_min")
        if base_min is not None:
            base_min = float(base_min)
            if not (0.01 <= base_min <= 180):
                return {"code": "bad_time_control", "message": "Base time out of range"}
        inc_sec = int(tc.get("inc_sec") or 0)
        if not (0 <= inc_sec <= 60):
            return {"code": "bad_time_control", "message": "Increment out of range"}
        rated = bool(data.get("rated", True))
        key = matchmaking.PoolKey(base_min=base_min, inc_sec=inc_sec, rated=rated)
        opponent = await matchmaking.join(user_id, key)
        if opponent is not None:
            await _start_game(opponent, user_id, base_min, inc_sec, rated)
        else:
            await manager.send_user(user_id, {"type": "queue:waiting", "data": {}})
        return None

    if mtype == "queue:leave":
        await matchmaking.leave(user_id)
        return None

    game = game_service.get_live(int(data.get("game_id") or 0))

    if mtype == "game:rejoin":
        if game is None:
            return {"code": "not_found", "message": "No such live game"}
        if game.player_color(user_id) is not None:
            game_service.handle_reconnect(game, user_id)
            await manager.send_room(
                game.id, {"type": "game:opponent_connection", "data": {"connected": True}}
            )
        manager.join_room(game.id, user_id)  # players and spectators alike
        await manager.send_user(user_id, {"type": "game:state", "data": game.state_payload()})
        if game.bot_level is not None:
            asyncio.create_task(_drive_bot(game))  # noqa: RUF006 — fire and forget
        if game.coach_level is not None and game.last_eval_cp is None and not game.moves:
            # Baseline eval for the eval bar at game start.
            asyncio.create_task(_coach_after_move(game, moved_by="b"))  # noqa: RUF006
        return None

    if game is None:
        return {"code": "not_found", "message": "No such live game"}

    try:
        if mtype == "game:move":
            uci = f"{data.get('from', '')}{data.get('to', '')}{data.get('promo', '')}"
            payload = await game_service.make_move(game, user_id, uci)
            # Always broadcast — clients need the FINAL position too (game:over
            # has already been sent by on_over when the move ended the game).
            await manager.send_room(game.id, {"type": "game:move", "data": payload})
            if payload.get("status") == "active":
                if game.coach_level is not None:
                    await _coach_after_move(game, moved_by="w")
                if game.bot_level is not None:
                    asyncio.create_task(_drive_bot(game))  # noqa: RUF006
        elif mtype == "coach:hint":
            if game.coach_level is None:
                return {"code": "no_coach", "message": "Not a Learn game"}
            hints_left, _ = _coach_budgets(game)
            if hints_left is not None and hints_left <= 0:
                return {"code": "no_hints", "message": "No hints left at this coach level"}
            best = await coach_service.best_move(game.board.fen())
            if best is None:
                return {"code": "engine_down", "message": "The coach is unavailable right now"}
            game.hints_used += 1
            hints_left, _ = _coach_budgets(game)
            await manager.send_user(
                user_id, {"type": "coach:hint", "data": {"move": best, "hints_left": hints_left}}
            )
        elif mtype == "coach:takeback":
            payload = await game_service.takeback(game, user_id)
            await manager.send_room(game.id, {"type": "game:state", "data": payload})
        elif mtype == "coach:premove":
            if game.coach_level is None:
                return {"code": "no_coach", "message": "Not a Learn game"}
            verdict = await _premove_verdict(game, data)
            await manager.send_user(user_id, {"type": "coach:premove_verdict", "data": verdict})
        elif mtype == "game:resign":
            await game_service.resign(game, user_id)
        elif mtype == "game:draw_offer":
            await game_service.offer_draw(game, user_id)
            await manager.send_room(game.id, {"type": "game:draw_offer", "data": {"by": user_id}})
        elif mtype == "game:draw_respond":
            accepted = await game_service.respond_draw(game, user_id, bool(data.get("accept")))
            if not accepted:
                await manager.send_room(game.id, {"type": "game:draw_declined", "data": {}})
        else:
            return {"code": "unknown_type", "message": f"Unknown message type {mtype!r}"}
    except MoveError as exc:
        return {"code": exc.code, "message": str(exc)}
    return None


async def _premove_verdict(game: LiveGame, data: dict[str, Any]) -> dict[str, Any]:
    """L1 blunder-confirm: score the intended move WITHOUT playing it."""
    frm, to, promo = str(data.get("from", "")), str(data.get("to", "")), str(data.get("promo", ""))
    echo = {"from": frm, "to": to, "promo": promo}
    try:
        move = chess.Move.from_uci(f"{frm}{to}{promo}")
    except ValueError:
        return {**echo, "ok": False, "legal": False}
    board = game.board.copy()
    if (
        move.promotion is None
        and board.piece_type_at(move.from_square) == chess.PAWN
        and chess.square_rank(move.to_square) in (0, 7)
    ):
        move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
    if move not in board.legal_moves:
        return {**echo, "ok": False, "legal": False}
    before = game.last_eval_cp
    if before is None:
        before = await coach_service.evaluate(board.fen(), depth=coach_service.PREMOVE_DEPTH)
    board.push(move)
    after = await coach_service.evaluate(board.fen(), depth=coach_service.PREMOVE_DEPTH)
    if before is None or after is None:
        return {**echo, "ok": True, "legal": True}  # engine down → don't block play
    drop = coach_service.win_pct(before) - coach_service.win_pct(after)
    tag = coach_service.tag_from_drop(drop)
    return {**echo, "ok": tag not in ("mistake", "blunder"), "legal": True, "tag": tag}


@router.websocket("/ws/game")
async def ws_game(ws: WebSocket) -> None:
    user_id = await _authenticate(ws)
    if user_id is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    manager.connect(user_id, ws)
    await writer.record_activity(user_id=user_id, kind="game")
    try:
        while True:
            msg = await ws.receive_json()
            error = await _handle(user_id, msg)
            if error is not None:
                await ws.send_json({"type": "error", "data": error})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, ws)
        await matchmaking.leave(user_id)
        if not manager.user_connected(user_id):
            for game in list(game_service._registry.values()):  # noqa: SLF001
                if game.player_color(user_id) is not None and game.status == "active":
                    await game_service.handle_disconnect(game, user_id)
                    await manager.send_room(
                        game.id,
                        {"type": "game:opponent_connection", "data": {"connected": False}},
                    )
