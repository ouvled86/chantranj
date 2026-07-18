"""Learning path: stages, items, per-user progress, puzzle bank."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import JsonDict


class ItemKind(enum.StrEnum):
    LESSON = "LESSON"
    DRILL = "DRILL"
    BOSS = "BOSS"


class ProgressStatus(enum.StrEnum):
    DONE = "DONE"


class Stage(Base):
    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    intro: Mapped[str] = mapped_column(Text, default="")
    order_idx: Mapped[int] = mapped_column(index=True)
    published: Mapped[bool] = mapped_column(default=True)


class LearnItem(Base):
    __tablename__ = "learn_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    kind: Mapped[ItemKind] = mapped_column(SAEnum(ItemKind, native_enum=False, length=8))
    title: Mapped[str] = mapped_column(String(120))
    sub: Mapped[str] = mapped_column(String(255), default="")
    order_idx: Mapped[int] = mapped_column(index=True)
    content_json: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict)
    boss_config: Mapped[dict[str, Any] | None] = mapped_column(JsonDict)
    published: Mapped[bool] = mapped_column(default=True)
    version: Mapped[int] = mapped_column(default=1)


class ItemProgress(Base):
    __tablename__ = "item_progress"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("learn_items.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[ProgressStatus] = mapped_column(
        SAEnum(ProgressStatus, native_enum=False, length=8), default=ProgressStatus.DONE
    )
    score: Mapped[int | None]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PuzzleBank(Base):
    __tablename__ = "puzzle_bank"

    id: Mapped[int] = mapped_column(primary_key=True)
    fen: Mapped[str] = mapped_column(String(100))
    line: Mapped[list[Any]] = mapped_column(JsonDict, default=list)
    themes: Mapped[list[Any]] = mapped_column(JsonDict, default=list)
    difficulty: Mapped[int] = mapped_column(default=1200, index=True)
    source: Mapped[str] = mapped_column(String(64), default="")
