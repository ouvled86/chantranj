"""Achievements and streaks (XP lives in the xp_events hypertable)."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import JsonDict


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(255))
    icon: Mapped[str] = mapped_column(String(16), default="◆")
    category: Mapped[str] = mapped_column(String(32), index=True)
    condition_json: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict)
    xp: Mapped[int] = mapped_column(default=50)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True
    )
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Streak(Base):
    __tablename__ = "streaks"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    current: Mapped[int] = mapped_column(default=0)
    best: Mapped[int] = mapped_column(default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date)
    freezes_left: Mapped[int] = mapped_column(default=1)
