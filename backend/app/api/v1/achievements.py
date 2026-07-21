"""Achievements catalogue with the caller's unlock state."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models import Achievement, UserAchievement
from app.schemas.stats import AchievementView

router = APIRouter(prefix="/achievements", tags=["achievements"])

CATEGORY_ORDER = ["learning", "tactics", "playing", "social", "dedication"]


@router.get("")
async def list_achievements(user: CurrentUser, db: DbDep) -> list[AchievementView]:
    achievements = (await db.scalars(select(Achievement))).all()
    unlocked = {
        ua.achievement_id: ua.unlocked_at
        for ua in (
            await db.scalars(
                select(UserAchievement).where(UserAchievement.user_id == user.id)
            )
        ).all()
    }
    views = [
        AchievementView(
            slug=a.slug,
            title=a.title,
            description=a.description,
            icon=a.icon,
            category=a.category,
            xp=a.xp,
            unlocked=a.id in unlocked,
            unlocked_at=str(unlocked[a.id]) if a.id in unlocked and unlocked[a.id] else None,
        )
        for a in achievements
    ]
    views.sort(
        key=lambda v: (
            CATEGORY_ORDER.index(v.category) if v.category in CATEGORY_ORDER else 99,
            not v.unlocked,
            v.xp,
        )
    )
    return views
