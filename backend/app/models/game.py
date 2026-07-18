"""Games, reviews and per-mode ratings."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import JsonDict


class GameMode(enum.StrEnum):
    ONLINE = "ONLINE"  # human vs human, no live review
    LEARN = "LEARN"  # bot + live coaching (coach_level 1-5)
    BOT = "BOT"  # bot arena, no assistance


class GameResult(enum.StrEnum):
    WHITE = "WHITE"
    BLACK = "BLACK"
    DRAW = "DRAW"
    ABORTED = "ABORTED"


class RatingMode(enum.StrEnum):
    ONLINE = "ONLINE"
    BOT = "BOT"
    DUEL = "DUEL"


class Rating(Base):
    __tablename__ = "ratings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    mode: Mapped[RatingMode] = mapped_column(
        SAEnum(RatingMode, native_enum=False, length=8), primary_key=True
    )
    value: Mapped[int] = mapped_column(default=1200)
    games: Mapped[int] = mapped_column(default=0)

    @property
    def provisional(self) -> bool:
        return self.games < 30


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[GameMode] = mapped_column(SAEnum(GameMode, native_enum=False, length=8))
    white_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    black_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    bot_level: Mapped[int | None]  # 1-8, set when one side is the engine
    coach_level: Mapped[int | None]  # 1-5, LEARN mode only
    time_control: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict)
    start_fen: Mapped[str | None] = mapped_column(String(100))  # None = standard start
    pgn: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[GameResult | None] = mapped_column(
        SAEnum(GameResult, native_enum=False, length=8)
    )
    end_reason: Mapped[str | None] = mapped_column(String(32))
    rated: Mapped[bool] = mapped_column(default=False)
    rating_delta_w: Mapped[int | None]
    rating_delta_b: Mapped[int | None]
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GameReview(Base):
    __tablename__ = "game_reviews"

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    moves_analysis: Mapped[list[Any]] = mapped_column(JsonDict, default=list)
    accuracy_w: Mapped[float | None]
    accuracy_b: Mapped[float | None]
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
