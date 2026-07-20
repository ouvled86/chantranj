"""Leaderboards — top ratings per mode, global or friends-only."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError
from app.models import Rating, RatingMode, User
from app.services import friends as friend_service

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])


class LeaderRow(BaseModel):
    rank: int
    username: str
    value: int
    games: int
    is_me: bool


@router.get("/{mode}")
async def leaderboard(
    mode: str,
    user: CurrentUser,
    db: DbDep,
    scope: str = Query(default="global", pattern="^(global|friends)$"),
    limit: int = Query(default=25, ge=1, le=100),
) -> list[LeaderRow]:
    try:
        rating_mode = RatingMode(mode.upper())
    except ValueError as exc:
        raise AppError(404, "bad_mode", "Unknown leaderboard") from exc

    stmt = (
        select(Rating, User)
        .join(User, User.id == Rating.user_id)
        .where(Rating.mode == rating_mode, Rating.games > 0, User.banned.is_(False))
        .order_by(Rating.value.desc())
    )
    if scope == "friends":
        ids = await friend_service.list_friend_ids(db, user.id)
        ids.append(user.id)
        stmt = stmt.where(Rating.user_id.in_(ids))

    rows = (await db.execute(stmt.limit(limit))).all()
    return [
        LeaderRow(
            rank=i + 1,
            username=u.username,
            value=r.value,
            games=r.games,
            is_me=u.id == user.id,
        )
        for i, (r, u) in enumerate(rows)
    ]
