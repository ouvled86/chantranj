"""In-process presence registry — who's online and what they're doing.

Shared by the /ws/social handler (writes) and REST (reads). Single-worker
correct; a Redis-backed presence set is the Phase 9 scaling swap.
"""

from typing import Literal

Status = Literal["online", "in_game", "in_duel"]

# user_id -> number of live social sockets (a user may have several tabs)
_connections: dict[int, int] = {}
# user_id -> activity status (defaults to "online" while connected)
_status: dict[int, Status] = {}


def connect(user_id: int) -> bool:
    """Returns True if this is the user's first connection (went online)."""
    first = _connections.get(user_id, 0) == 0
    _connections[user_id] = _connections.get(user_id, 0) + 1
    if first:
        _status[user_id] = "online"
    return first


def disconnect(user_id: int) -> bool:
    """Returns True if the user's last connection closed (went offline)."""
    remaining = _connections.get(user_id, 0) - 1
    if remaining <= 0:
        _connections.pop(user_id, None)
        _status.pop(user_id, None)
        return True
    _connections[user_id] = remaining
    return False


def set_status(user_id: int, status: Status) -> None:
    if user_id in _connections:
        _status[user_id] = status


def is_online(user_id: int) -> bool:
    return user_id in _connections


def status_of(user_id: int) -> str:
    return _status.get(user_id, "offline")


def reset() -> None:
    """Test hook."""
    _connections.clear()
    _status.clear()
