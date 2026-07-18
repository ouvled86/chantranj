"""telemetry hypertables + compression/retention + continuous aggregates

The homelab mirror: game events flow into TimescaleDB exactly like vehicle
telemetry. PostgreSQL/TimescaleDB only — no-op on other dialects.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HYPERTABLES = (
    "move_events",
    "clock_ticks",
    "rating_history",
    "xp_events",
    "engine_samples",
    "activity_events",
)


def _is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.create_table(
        "move_events",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger()),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(1), nullable=False),
        sa.Column("uci", sa.String(8), nullable=False),
        sa.Column("san", sa.String(12), nullable=False),
        sa.Column("clock_ms", sa.BigInteger()),
        sa.Column("eval_cp", sa.Integer()),
        sa.Column("is_book", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tag", sa.String(16)),
    )
    op.create_index("ix_move_events_game_id", "move_events", ["game_id"])
    op.create_index("ix_move_events_user_id", "move_events", ["user_id"])

    op.create_table(
        "clock_ticks",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("white_ms", sa.BigInteger(), nullable=False),
        sa.Column("black_ms", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_clock_ticks_game_id", "clock_ticks", ["game_id"])

    op.create_table(
        "rating_history",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.BigInteger()),
    )
    op.create_index("ix_rating_history_user_id", "rating_history", ["user_id"])

    op.create_table(
        "xp_events",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(48), nullable=False),
        sa.Column("ref_id", sa.String(64)),
    )
    op.create_index("ix_xp_events_user_id", "xp_events", ["user_id"])

    op.create_table(
        "engine_samples",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("request_kind", sa.String(16), nullable=False),
        sa.Column("depth", sa.Integer()),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("queue_depth", sa.Integer()),
    )

    op.create_table(
        "activity_events",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
    )
    op.create_index("ix_activity_events_user_id", "activity_events", ["user_id"])

    # --- hypertables ---
    for table in HYPERTABLES:
        op.execute(
            f"SELECT create_hypertable('{table}', 'time', "
            f"chunk_time_interval => INTERVAL '7 days')"
        )

    # --- compression (chunks older than 7 days) ---
    compress_segments = {
        "move_events": "game_id",
        "clock_ticks": "game_id",
        "rating_history": "user_id",
        "xp_events": "user_id",
        "engine_samples": "request_kind",
        "activity_events": "user_id",
    }
    for table, segment in compress_segments.items():
        op.execute(
            f"ALTER TABLE {table} SET (timescaledb.compress, "
            f"timescaledb.compress_segmentby = '{segment}')"
        )
        op.execute(f"SELECT add_compression_policy('{table}', INTERVAL '7 days')")

    # --- retention: raw clock ticks are disposable after 30 days ---
    op.execute("SELECT add_retention_policy('clock_ticks', INTERVAL '30 days')")

    # --- continuous aggregates (must run outside a transaction) ---
    with op.get_context().autocommit_block():
        op.execute("""
            CREATE MATERIALIZED VIEW leaderboard_daily
            WITH (timescaledb.continuous) AS
            SELECT time_bucket('1 day', time) AS day,
                   user_id, mode,
                   last(value, time) AS value
            FROM rating_history
            GROUP BY day, user_id, mode
            WITH NO DATA
        """)
        op.execute("""
            CREATE MATERIALIZED VIEW player_accuracy_weekly
            WITH (timescaledb.continuous) AS
            SELECT time_bucket('7 days', time) AS week,
                   user_id,
                   avg(CASE WHEN tag IN ('inaccuracy','mistake','blunder')
                            THEN 0.0 ELSE 1.0 END) AS clean_move_ratio,
                   count(*) AS moves
            FROM move_events
            WHERE user_id IS NOT NULL AND tag IS NOT NULL
            GROUP BY week, user_id
            WITH NO DATA
        """)
        op.execute("""
            CREATE MATERIALIZED VIEW engine_latency_5m
            WITH (timescaledb.continuous) AS
            SELECT time_bucket('5 minutes', time) AS bucket,
                   request_kind,
                   avg(latency_ms) AS avg_ms,
                   max(latency_ms) AS max_ms,
                   count(*) AS requests
            FROM engine_samples
            GROUP BY bucket, request_kind
            WITH NO DATA
        """)
        op.execute("""
            CREATE MATERIALIZED VIEW activity_daily
            WITH (timescaledb.continuous) AS
            SELECT time_bucket('1 day', time) AS day,
                   user_id,
                   count(*) AS events
            FROM activity_events
            GROUP BY day, user_id
            WITH NO DATA
        """)

        for view, (start, every) in {
            "leaderboard_daily": ("3 days", "1 hour"),
            "player_accuracy_weekly": ("21 days", "6 hours"),
            "engine_latency_5m": ("1 hour", "5 minutes"),
            "activity_daily": ("3 days", "1 hour"),
        }.items():
            op.execute(
                f"SELECT add_continuous_aggregate_policy('{view}', "
                f"start_offset => INTERVAL '{start}', end_offset => INTERVAL '5 minutes', "
                f"schedule_interval => INTERVAL '{every}')"
            )


def downgrade() -> None:
    if not _is_postgres():
        return
    with op.get_context().autocommit_block():
        for view in (
            "activity_daily", "engine_latency_5m",
            "player_accuracy_weekly", "leaderboard_daily",
        ):
            op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {view}")
    for table in reversed(HYPERTABLES):
        op.drop_table(table)
