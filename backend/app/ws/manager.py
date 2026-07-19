"""WebSocket connection bookkeeping: sockets per user, users per game room."""

from typing import Any

import structlog
from fastapi import WebSocket

log = structlog.get_logger()


class ConnectionManager:
    def __init__(self) -> None:
        self.by_user: dict[int, set[WebSocket]] = {}
        self.rooms: dict[int, set[int]] = {}  # game_id -> user_ids

    def connect(self, user_id: int, ws: WebSocket) -> None:
        self.by_user.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        sockets = self.by_user.get(user_id)
        if sockets:
            sockets.discard(ws)
            if not sockets:
                self.by_user.pop(user_id, None)

    def user_connected(self, user_id: int) -> bool:
        return bool(self.by_user.get(user_id))

    def join_room(self, game_id: int, user_id: int) -> None:
        self.rooms.setdefault(game_id, set()).add(user_id)

    def drop_room(self, game_id: int) -> None:
        self.rooms.pop(game_id, None)

    async def send_user(self, user_id: int, message: dict[str, Any]) -> None:
        for ws in list(self.by_user.get(user_id, ())):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 — dead socket; cleanup happens on its recv loop
                log.debug("ws_send_failed", user_id=user_id)

    async def send_room(self, game_id: int, message: dict[str, Any]) -> None:
        for user_id in list(self.rooms.get(game_id, ())):
            await self.send_user(user_id, message)


game_manager = ConnectionManager()
