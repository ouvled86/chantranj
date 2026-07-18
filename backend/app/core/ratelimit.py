"""Fixed-window rate limiting: Redis-backed, with an in-process fallback so dev
and tests work without Redis (multi-worker prod correctness needs Redis)."""

import time

import structlog
from fastapi import Request
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.errors import AppError

log = structlog.get_logger()

_redis: Redis | None = None
_redis_broken = False
_memory_store: dict[str, tuple[int, float]] = {}


def reset_memory_store() -> None:
    """Test hook."""
    _memory_store.clear()


async def _get_redis() -> Redis | None:
    global _redis, _redis_broken
    if _redis_broken:
        return None
    if _redis is None:
        _redis = Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=0.5, socket_timeout=0.5
        )
    return _redis


class RateLimiter:
    """Dependency: `Depends(RateLimiter(times=5, seconds=60, scope="login"))`."""

    def __init__(self, times: int, seconds: int, scope: str) -> None:
        self.times = times
        self.seconds = seconds
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        global _redis_broken
        if not get_settings().rate_limit_enabled:
            return
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{self.scope}:{client_ip}"

        count: int | None = None
        redis = await _get_redis()
        if redis is not None:
            try:
                async with redis.pipeline(transaction=True) as pipe:
                    pipe.incr(key)
                    pipe.expire(key, self.seconds, nx=True)
                    count = int((await pipe.execute())[0])
            except Exception:  # noqa: BLE001 — any redis failure falls back to memory
                _redis_broken = True
                log.warning("ratelimit_redis_unavailable_falling_back")

        if count is None:
            now = time.monotonic()
            current, reset_at = _memory_store.get(key, (0, now + self.seconds))
            if now > reset_at:
                current, reset_at = 0, now + self.seconds
            count = current + 1
            _memory_store[key] = (count, reset_at)

        if count > self.times:
            raise AppError(429, "rate_limited", "Too many requests — slow down")
