"""Matchmaking queue — in-process FIFO per (time-control, rated) pool.

Single-worker correct. Redis-backed pool + rating-band widening arrive with
Docker (TASKS 4.4 note). Anti-self-match enforced.
"""

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class PoolKey:
    base_min: float | None
    inc_sec: int
    rated: bool


_pools: dict[PoolKey, list[int]] = {}
_lock = asyncio.Lock()


async def join(user_id: int, key: PoolKey) -> int | None:
    """Returns an opponent user_id if matched, else None (queued)."""
    async with _lock:
        pool = _pools.setdefault(key, [])
        if user_id in pool:
            return None
        for i, other in enumerate(pool):
            if other != user_id:
                pool.pop(i)
                return other
        pool.append(user_id)
        return None


async def leave(user_id: int) -> None:
    async with _lock:
        for pool in _pools.values():
            if user_id in pool:
                pool.remove(user_id)


def reset() -> None:
    """Test hook."""
    _pools.clear()
