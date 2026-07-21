"""/ws/duel — matchmaking + the live Puzzle Duel loop."""

import asyncio
from typing import Any

import jwt as pyjwt
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.db.session import get_session_factory
from app.models import User
from app.services import duel as duel_service
from app.services import presence
from app.ws.manager import ConnectionManager

log = structlog.get_logger()
router = APIRouter()
duel_manager = ConnectionManager()

# users waiting for a matchmade duel
_queue: list[int] = []
_lock = asyncio.Lock()


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


async def _username(uid: int) -> str:
    async with get_session_factory()() as db:
        u = await db.get(User, uid)
        return u.username if u else "?"


async def _on_duel_over(duel: duel_service.LiveDuel, payload: dict[str, Any]) -> None:
    from app.services import gamification

    sa, sb = payload["score_a"], payload["score_b"]
    async with get_session_factory()() as db:
        for uid in (duel.a_id, duel.b_id):
            mine, theirs = (sa, sb) if uid == duel.a_id else (sb, sa)
            event = "duel_win" if mine > theirs else "duel_draw" if mine == theirs else "duel_loss"
            reward = await gamification.on_event(db, uid, event, ref=str(duel.id))
            presence.set_status(uid, "online")
            await duel_manager.send_user(
                uid,
                {
                    "type": "duel:over",
                    "data": {
                        "your_score": mine,
                        "opp_score": theirs,
                        "rating_delta": payload["rating_delta"].get(uid, 0),
                        "reward": reward,
                    },
                },
            )
    duel_manager.drop_room(duel.id)


async def _start_duel(a_id: int, b_id: int) -> None:
    duel = await duel_service.create_duel(a_id, b_id, on_over=_on_duel_over)
    if duel is None:
        err = {"type": "error", "data": {"code": "no_puzzles", "message": "No puzzles available"}}
        for uid in (a_id, b_id):
            await duel_manager.send_user(uid, err)
        return
    names = {a_id: await _username(a_id), b_id: await _username(b_id)}
    for uid in (a_id, b_id):
        presence.set_status(uid, "in_duel")
        duel_manager.join_room(duel.id, uid)
        await duel_manager.send_user(
            uid,
            {
                "type": "duel:start",
                "data": {
                    "duel_id": duel.id,
                    "opponent": names[duel.opponent(uid)],
                    **duel.puzzle_payload(uid),
                },
            },
        )


async def _handle(user_id: int, msg: dict[str, Any]) -> dict[str, Any] | None:
    mtype = msg.get("type")
    data = msg.get("data") or {}

    if mtype == "duel:queue":
        async with _lock:
            if user_id in _queue:
                return None
            opponent = next((u for u in _queue if u != user_id), None)
            if opponent is None:
                _queue.append(user_id)
                await duel_manager.send_user(user_id, {"type": "duel:waiting", "data": {}})
                return None
            _queue.remove(opponent)
        await _start_duel(opponent, user_id)
        return None

    if mtype == "duel:leave":
        async with _lock:
            if user_id in _queue:
                _queue.remove(user_id)
        return None

    if mtype == "duel:submit":
        duel = duel_service.get_live(int(data.get("duel_id", 0)))
        if duel is None:
            return {"code": "not_found", "message": "No such duel"}
        if user_id not in (duel.a_id, duel.b_id):
            return {"code": "not_a_player", "message": "Not your duel"}
        uci = f"{data.get('from', '')}{data.get('to', '')}{data.get('promo', '')}"
        result = await duel_service.submit(duel, user_id, uci)
        await duel_manager.send_user(user_id, {"type": "duel:progress", "data": result})
        # opponent sees a live ticker
        await duel_manager.send_user(
            duel.opponent(user_id),
            {"type": "duel:opponent_progress", "data": duel.opponent_payload(user_id)},
        )
        return None

    return {"code": "unknown_type", "message": f"Unknown type {mtype!r}"}


@router.websocket("/ws/duel")
async def ws_duel(ws: WebSocket) -> None:
    user_id = await _authenticate(ws)
    if user_id is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    duel_manager.connect(user_id, ws)
    try:
        while True:
            msg = await ws.receive_json()
            error = await _handle(user_id, msg)
            if error is not None:
                await ws.send_json({"type": "error", "data": error})
    except WebSocketDisconnect:
        pass
    finally:
        duel_manager.disconnect(user_id, ws)
        async with _lock:
            if user_id in _queue:
                _queue.remove(user_id)


def _reset_queue() -> None:
    _queue.clear()
