"""Telemetry tables — TimescaleDB hypertables in production.

Defined as Core tables (not ORM): append-only event streams written by the
telemetry module. On PostgreSQL, migration 0003 converts them to hypertables
with compression/retention and continuous aggregates. On SQLite (tests) they
are plain tables, which is fine for asserting writes.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Table,
    func,
)

from app.db.base import Base

move_events = Table(
    "move_events",
    Base.metadata,
    Column("time", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("game_id", BigInteger, nullable=False, index=True),
    Column("user_id", BigInteger, index=True),  # denormalized for caggs; null = bot move
    Column("ply", Integer, nullable=False),
    Column("side", String(1), nullable=False),  # 'w' | 'b'
    Column("uci", String(8), nullable=False),
    Column("san", String(12), nullable=False),
    Column("clock_ms", BigInteger),
    Column("eval_cp", Integer),  # centipawns, engine POV=white; null until analysed
    Column("is_book", Boolean, nullable=False, default=False),
    Column("tag", String(16)),  # great/good/inaccuracy/mistake/blunder
)

clock_ticks = Table(
    "clock_ticks",
    Base.metadata,
    Column("time", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("game_id", BigInteger, nullable=False, index=True),
    Column("white_ms", BigInteger, nullable=False),
    Column("black_ms", BigInteger, nullable=False),
)

rating_history = Table(
    "rating_history",
    Base.metadata,
    Column("time", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("user_id", BigInteger, nullable=False, index=True),
    Column("mode", String(8), nullable=False),
    Column("value", Integer, nullable=False),
    Column("delta", Integer, nullable=False),
    Column("game_id", BigInteger),
)

xp_events = Table(
    "xp_events",
    Base.metadata,
    Column("time", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("user_id", BigInteger, nullable=False, index=True),
    Column("amount", Integer, nullable=False),
    Column("reason", String(48), nullable=False),
    Column("ref_id", String(64)),
)

engine_samples = Table(
    "engine_samples",
    Base.metadata,
    Column("time", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("request_kind", String(16), nullable=False),  # analyse | botmove | review
    Column("depth", Integer),
    Column("latency_ms", Float, nullable=False),
    Column("queue_depth", Integer),
)

activity_events = Table(
    "activity_events",
    Base.metadata,
    Column("time", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("user_id", BigInteger, nullable=False, index=True),
    Column("kind", String(16), nullable=False),  # login|lesson|drill|game|duel|puzzle
)
