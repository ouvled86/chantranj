"""/ws/game — the online-play socket. Contract in docs/ARCHITECTURE.md §5."""

from typing import Any

import jwt as pyjwt
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import get_session_factory
from app.models import RatingMode, User
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


async def _on_game_over(game: LiveGame, payload: dict[str, Any]) -> None:
    await manager.send_room(game.id, {"type": "game:over", "data": payload})
    manager.drop_room(game.id)


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
        on_over=_on_game_over,
    )
    manager.join_room(game.id, a_id)
    manager.join_room(game.id, b_id)

    async with get_session_factory()() as db:
        users = {
            u.id: u
            for u in (await db.scalars(select(User).where(User.id.in_([a_id, b_id])))).all()
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
        return None

    if game is None:
        return {"code": "not_found", "message": "No such live game"}

    try:
        if mtype == "game:move":
            uci = f"{data.get('from', '')}{data.get('to', '')}{data.get('promo', '')}"
            payload = await game_service.make_move(game, user_id, uci)
            if payload.get("status") == "active":
                await manager.send_room(game.id, {"type": "game:move", "data": payload})
        elif mtype == "game:resign":
            await game_service.resign(game, user_id)
        elif mtype == "game:draw_offer":
            await game_service.offer_draw(game, user_id)
            await manager.send_room(
                game.id, {"type": "game:draw_offer", "data": {"by": user_id}}
            )
        elif mtype == "game:draw_respond":
            accepted = await game_service.respond_draw(game, user_id, bool(data.get("accept")))
            if not accepted:
                await manager.send_room(game.id, {"type": "game:draw_declined", "data": {}})
        else:
            return {"code": "unknown_type", "message": f"Unknown message type {mtype!r}"}
    except MoveError as exc:
        return {"code": exc.code, "message": str(exc)}
    return None


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
