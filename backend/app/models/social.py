"""Friendships and puzzle duels."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import JsonDict


class FriendshipStatus(enum.StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    BLOCKED = "BLOCKED"


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_friend_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    addressee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[FriendshipStatus] = mapped_column(
        SAEnum(FriendshipStatus, native_enum=False, length=8), default=FriendshipStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DuelMatch(Base):
    __tablename__ = "duel_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_a_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    player_b_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    puzzle_ids: Mapped[list[Any]] = mapped_column(JsonDict, default=list)
    score_a: Mapped[int] = mapped_column(default=0)
    score_b: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
