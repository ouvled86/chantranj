"""/ws/social — presence + friend challenges.

Presence changes fan out to a user's friends; challenges are relayed peer to
peer and, on accept, spawn a real online game the two players rejoin via
/ws/game (reusing the whole online-play path).
"""

import uuid
from typing import Any

import jwt as pyjwt
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.db.session import get_session_factory
from app.models import User
from app.services import friends as friend_service
from app.services import presence
from app.ws.manager import ConnectionManager

log = structlog.get_logger()
router = APIRouter()
social_manager = ConnectionManager()

# challenge_id -> {from, to, time_control, rated}
_pending: dict[str, dict[str, Any]] = {}


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


async def _friend_ids(user_id: int) -> list[int]:
    async with get_session_factory()() as db:
        return await friend_service.list_friend_ids(db, user_id)


async def broadcast_presence(user_id: int, status: str) -> None:
    """Tell this user's online friends about their new status."""
    for fid in await _friend_ids(user_id):
        await social_manager.send_user(
            fid, {"type": "friend:presence", "data": {"user_id": user_id, "status": status}}
        )


async def _username(user_id: int) -> str:
    async with get_session_factory()() as db:
        u = await db.get(User, user_id)
        return u.username if u else "?"


async def _handle(user_id: int, msg: dict[str, Any]) -> dict[str, Any] | None:
    mtype = msg.get("type")
    data = msg.get("data") or {}

    if mtype == "challenge:send":
        target_id = int(data.get("to_user_id", 0))
        async with get_session_factory()() as db:
            if not await friend_service.are_friends(db, user_id, target_id):
                return {"code": "not_friends", "message": "You can only challenge friends"}
        if not presence.is_online(target_id):
            return {"code": "offline", "message": "That friend is offline"}
        challenge_id = uuid.uuid4().hex[:12]
        tc = data.get("time_control") or {"base_min": 5, "inc_sec": 0}
        _pending[challenge_id] = {
            "from": user_id,
            "to": target_id,
            "time_control": tc,
            "rated": bool(data.get("rated", False)),
        }
        await social_manager.send_user(
            target_id,
            {
                "type": "challenge:receive",
                "data": {
                    "challenge_id": challenge_id,
                    "from_user_id": user_id,
                    "from_username": await _username(user_id),
                    "time_control": tc,
                    "rated": _pending[challenge_id]["rated"],
                },
            },
        )
        return None

    if mtype == "challenge:accept":
        ch = _pending.pop(str(data.get("challenge_id", "")), None)
        if ch is None or ch["to"] != user_id:
            return {"code": "expired", "message": "That challenge expired"}
        await _spawn_challenge_game(ch)
        return None

    if mtype == "challenge:decline":
        ch = _pending.pop(str(data.get("challenge_id", "")), None)
        if ch is not None:
            await social_manager.send_user(
                ch["from"], {"type": "challenge:declined", "data": {}}
            )
        return None

    if mtype == "status:set":
        status = str(data.get("status", "online"))
        if status in ("online", "in_game", "in_duel"):
            presence.set_status(user_id, status)  # type: ignore[arg-type]
            await broadcast_presence(user_id, status)
        return None

    return {"code": "unknown_type", "message": f"Unknown type {mtype!r}"}


async def _spawn_challenge_game(ch: dict[str, Any]) -> None:
    """Challenger plays white. Both get a challenge:ready with their colour."""
    from app.services import games as game_service
    from app.ws.game import on_game_over
    from app.ws.manager import game_manager

    tc = ch["time_control"]
    game = await game_service.create_game(
        white_id=ch["from"],
        black_id=ch["to"],
        rated=ch["rated"],
        base_min=tc.get("base_min"),
        inc_sec=tc.get("inc_sec", 0),
        on_over=on_game_over,
    )
    game_manager.join_room(game.id, ch["from"])
    game_manager.join_room(game.id, ch["to"])
    for uid, color in ((ch["from"], "w"), (ch["to"], "b")):
        await social_manager.send_user(
            uid, {"type": "challenge:ready", "data": {"game_id": game.id, "color": color}}
        )


@router.websocket("/ws/social")
async def ws_social(ws: WebSocket) -> None:
    user_id = await _authenticate(ws)
    if user_id is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    social_manager.connect(user_id, ws)
    if presence.connect(user_id):
        await broadcast_presence(user_id, "online")
    try:
        while True:
            msg = await ws.receive_json()
            error = await _handle(user_id, msg)
            if error is not None:
                await ws.send_json({"type": "error", "data": error})
    except WebSocketDisconnect:
        pass
    finally:
        social_manager.disconnect(user_id, ws)
        if presence.disconnect(user_id):
            await broadcast_presence(user_id, "offline")
