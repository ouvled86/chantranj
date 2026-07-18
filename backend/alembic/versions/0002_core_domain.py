"""ratings, games, reviews, friendships, curriculum, gamification, duels

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-19

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB_EMPTY_OBJ = sa.text("'{}'::jsonb")
JSONB_EMPTY_ARR = sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.create_table(
        "ratings",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("mode", sa.String(8), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("games", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("white_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("black_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("bot_level", sa.Integer()),
        sa.Column("coach_level", sa.Integer()),
        sa.Column("time_control", JSONB(), nullable=False, server_default=JSONB_EMPTY_OBJ),
        sa.Column("start_fen", sa.String(100)),
        sa.Column("pgn", sa.Text(), nullable=False, server_default=""),
        sa.Column("result", sa.String(8)),
        sa.Column("end_reason", sa.String(32)),
        sa.Column("rated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rating_delta_w", sa.Integer()),
        sa.Column("rating_delta_b", sa.Integer()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_games_white_id", "games", ["white_id"])
    op.create_index("ix_games_black_id", "games", ["black_id"])

    op.create_table(
        "game_reviews",
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("moves_analysis", JSONB(), nullable=False, server_default=JSONB_EMPTY_ARR),
        sa.Column("accuracy_w", sa.Float()),
        sa.Column("accuracy_b", sa.Float()),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("addressee_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(8), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friend_pair"),
    )
    op.create_index("ix_friendships_requester_id", "friendships", ["requester_id"])
    op.create_index("ix_friendships_addressee_id", "friendships", ["addressee_id"])

    op.create_table(
        "stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("intro", sa.Text(), nullable=False, server_default=""),
        sa.Column("order_idx", sa.Integer(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug", name="uq_stages_slug"),
    )
    op.create_index("ix_stages_order_idx", "stages", ["order_idx"])

    op.create_table(
        "learn_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stage_id", sa.Integer(), sa.ForeignKey("stages.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("sub", sa.String(255), nullable=False, server_default=""),
        sa.Column("order_idx", sa.Integer(), nullable=False),
        sa.Column("content_json", JSONB(), nullable=False, server_default=JSONB_EMPTY_OBJ),
        sa.Column("boss_config", JSONB()),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("slug", name="uq_learn_items_slug"),
    )
    op.create_index("ix_learn_items_stage_id", "learn_items", ["stage_id"])
    op.create_index("ix_learn_items_order_idx", "learn_items", ["order_idx"])

    op.create_table(
        "item_progress",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("item_id", sa.Integer(),
                  sa.ForeignKey("learn_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(8), nullable=False, server_default="DONE"),
        sa.Column("score", sa.Integer()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "puzzle_bank",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fen", sa.String(100), nullable=False),
        sa.Column("line", JSONB(), nullable=False, server_default=JSONB_EMPTY_ARR),
        sa.Column("themes", JSONB(), nullable=False, server_default=JSONB_EMPTY_ARR),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("source", sa.String(64), nullable=False, server_default=""),
    )
    op.create_index("ix_puzzle_bank_difficulty", "puzzle_bank", ["difficulty"])

    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(16), nullable=False, server_default="◆"),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("condition_json", JSONB(), nullable=False, server_default=JSONB_EMPTY_OBJ),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="50"),
        sa.UniqueConstraint("slug", name="uq_achievements_slug"),
    )
    op.create_index("ix_achievements_category", "achievements", ["category"])

    op.create_table(
        "user_achievements",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("achievement_id", sa.Integer(),
                  sa.ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("unlocked_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "streaks",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_date", sa.Date()),
        sa.Column("freezes_left", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "duel_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_a_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("player_b_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("puzzle_ids", JSONB(), nullable=False, server_default=JSONB_EMPTY_ARR),
        sa.Column("score_a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_b", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in (
        "duel_matches", "streaks", "user_achievements", "achievements", "puzzle_bank",
        "item_progress", "learn_items", "stages", "friendships", "game_reviews",
        "games", "ratings",
    ):
        op.drop_table(table)
