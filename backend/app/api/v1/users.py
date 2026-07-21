"""User endpoints: own profile (GET/PATCH), stats, public profiles."""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError
from app.models import (
    Achievement,
    Game,
    GameResult,
    ItemProgress,
    Rating,
    RatingMode,
    Streak,
    UserAchievement,
)
from app.models.user import User
from app.schemas.stats import MeStats, RatingBlock, RatingPoint
from app.schemas.user import PublicUser, UserOut, UserPatch
from app.services import gamification

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/me/stats")
async def my_stats(user: CurrentUser, db: DbDep) -> MeStats:
    total = await gamification.total_xp(db, user.id)
    level = gamification.level_for_xp(total)

    ratings: dict[str, RatingBlock] = {}
    for mode in RatingMode:
        r = await db.get(Rating, (user.id, mode))
        ratings[mode.value.lower()] = RatingBlock(
            value=r.value if r else 1200,
            games=r.games if r else 0,
            provisional=(r.games if r else 0) < 30,
        )

    streak = await db.get(Streak, user.id)
    games_played = await db.scalar(
        select(func.count()).select_from(Game).where(
            ((Game.white_id == user.id) | (Game.black_id == user.id)) & Game.result.isnot(None)
        )
    )
    wins = await db.scalar(
        select(func.count()).select_from(Game).where(
            ((Game.white_id == user.id) & (Game.result == GameResult.WHITE))
            | ((Game.black_id == user.id) & (Game.result == GameResult.BLACK))
        )
    )
    items_done = await db.scalar(
        select(func.count()).select_from(ItemProgress).where(ItemProgress.user_id == user.id)
    )
    ach_total = await db.scalar(select(func.count()).select_from(Achievement))
    ach_unlocked = await db.scalar(
        select(func.count()).select_from(UserAchievement).where(
            UserAchievement.user_id == user.id
        )
    )

    return MeStats(
        level=level,
        total_xp=total,
        xp_into_level=total - gamification.xp_for_level(level),
        xp_for_next=gamification.xp_for_level(level + 1) - gamification.xp_for_level(level),
        streak=streak.current if streak else 0,
        best_streak=streak.best if streak else 0,
        freezes_left=streak.freezes_left if streak else 1,
        ratings=ratings,
        games_played=int(games_played or 0),
        wins=int(wins or 0),
        items_done=int(items_done or 0),
        achievements_unlocked=int(ach_unlocked or 0),
        achievements_total=int(ach_total or 0),
    )


@router.get("/me/ratings/{mode}")
async def rating_history(mode: str, user: CurrentUser, db: DbDep) -> list[RatingPoint]:
    from app.models.telemetry import rating_history as rh

    try:
        rating_mode = RatingMode(mode.upper())
    except ValueError as exc:
        raise AppError(404, "bad_mode", "Unknown mode") from exc
    rows = (
        await db.execute(
            select(rh.c.time, rh.c.value)
            .where(rh.c.user_id == user.id, rh.c.mode == rating_mode.value)
            .order_by(rh.c.time)
        )
    ).all()
    return [RatingPoint(time=str(t), value=v) for t, v in rows]


@router.patch("/me")
async def patch_me(data: UserPatch, user: CurrentUser, db: DbDep) -> UserOut:
    if data.username is not None and data.username != user.username:
        taken = await db.scalar(select(User).where(User.username == data.username))
        if taken is not None:
            raise AppError(409, "already_exists", "That username is already taken")
        user.username = data.username
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    if data.settings is not None:
        user.settings = data.settings
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/{username}")
async def public_profile(username: str, db: DbDep) -> PublicUser:
    user = await db.scalar(select(User).where(User.username == username))
    if user is None or user.banned:
        raise AppError(404, "not_found", "No such player")
    return PublicUser.model_validate(user)
