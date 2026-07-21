"""Lazy async engine + session dependency.

SQLite (tests) gets a StaticPool so the in-memory DB survives across connections.
"""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        kwargs: dict[str, Any] = {"pool_pre_ping": True}
        is_sqlite = url.startswith("sqlite")
        if is_sqlite:
            # timeout makes writers wait on a lock instead of erroring.
            kwargs = {"connect_args": {"check_same_thread": False, "timeout": 30}}
            # Only :memory: needs StaticPool (one shared conn); a file DB is
            # safe with independent connections and survives cross-loop tests.
            if ":memory:" in url:
                kwargs["poolclass"] = StaticPool
        _engine = create_async_engine(url, **kwargs)
        if is_sqlite and ":memory:" not in url:
            # WAL + busy_timeout dramatically reduce "database is locked" under
            # the concurrent writers a live game produces (watchdog, moves, XP).
            @event.listens_for(_engine.sync_engine, "connect")
            def _sqlite_pragmas(dbapi_conn: Any, _rec: Any) -> None:
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA busy_timeout=30000")
                cur.close()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
