"""Gamification: XP ledger, levels, streaks, and the achievement engine.

XP lives in the xp_events hypertable (append-only). Level is derived from total
XP, never stored. Achievements are evaluated from durable domain data so they're
correct even if an event is missed — the trigger just prompts a re-check.
"""

from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.models import (
    Achievement,
    DuelMatch,
    Game,
    GameMode,
    GameResult,
    ItemKind,
    ItemProgress,
    LearnItem,
    Stage,
    Streak,
    UserAchievement,
)
from app.models.telemetry import xp_events

log = structlog.get_logger()

# Base XP per event kind.
XP = {
    "item": 20,
    "boss": 100,
    "game_win": 25,
    "game_draw": 12,
    "game_loss": 5,
    "duel_win": 30,
    "duel_draw": 15,
    "duel_loss": 8,
    "streak_day": 15,
}

LEVEL_COEFF = 100.0
LEVEL_EXP = 1.6


def xp_for_level(n: int) -> int:
    """Total XP required to *reach* level n. Level 1 is 0 XP."""
    return 0 if n <= 1 else int(LEVEL_COEFF * (n - 1) ** LEVEL_EXP)


def level_for_xp(total_xp: int) -> int:
    """Highest level whose threshold is covered. Defined by iterating the real
    thresholds so it round-trips with xp_for_level despite int() truncation."""
    n = 1
    while xp_for_level(n + 1) <= total_xp:
        n += 1
    return n


async def total_xp(db: AsyncSession, user_id: int) -> int:
    total = await db.scalar(
        select(func.coalesce(func.sum(xp_events.c.amount), 0)).where(
            xp_events.c.user_id == user_id
        )
    )
    return int(total or 0)


async def _award_xp(
    db: AsyncSession, user_id: int, amount: int, reason: str, ref: str | None
) -> None:
    await db.execute(
        xp_events.insert(),
        [{"user_id": user_id, "amount": amount, "reason": reason, "ref_id": ref}],
    )


async def touch_streak(db: AsyncSession, user_id: int) -> tuple[int, bool]:
    """Register activity today. Returns (current_streak, is_new_day)."""
    streak = await db.get(Streak, user_id)
    today = now_utc().date()
    if streak is None:
        streak = Streak(user_id=user_id, current=1, best=1, last_active_date=today, freezes_left=1)
        db.add(streak)
        return 1, True
    if streak.last_active_date == today:
        return streak.current, False
    yesterday = today - timedelta(days=1)
    if streak.last_active_date == yesterday:
        streak.current += 1
    elif streak.last_active_date == today - timedelta(days=2) and streak.freezes_left > 0:
        streak.freezes_left -= 1  # a freeze covers one missed day
        streak.current += 1
    else:
        streak.current = 1
    streak.best = max(streak.best, streak.current)
    streak.last_active_date = today
    # weekly freeze top-up
    if streak.freezes_left < 1:
        streak.freezes_left = 1
    return streak.current, True


# ---- achievement progress registry ----

async def _count_items_done(db: AsyncSession, uid: int, kind: ItemKind | None = None) -> int:
    stmt = (
        select(func.count())
        .select_from(ItemProgress)
        .join(LearnItem, LearnItem.id == ItemProgress.item_id)
        .where(ItemProgress.user_id == uid)
    )
    if kind is not None:
        stmt = stmt.where(LearnItem.kind == kind)
    return int(await db.scalar(stmt) or 0)


async def _game_wins(db: AsyncSession, uid: int, **filters: Any) -> int:
    won = select(Game).where(
        ((Game.white_id == uid) & (Game.result == GameResult.WHITE))
        | ((Game.black_id == uid) & (Game.result == GameResult.BLACK))
    )
    if filters.get("reason"):
        won = won.where(Game.end_reason == filters["reason"])
    rows = (await db.scalars(won)).all()
    if filters.get("time_class") == "classical":
        rows = [g for g in rows if ((g.time_control or {}).get("base_min") or 0) >= 30]
    return len(rows)


async def _stage_done(db: AsyncSession, uid: int, stage_order: int) -> bool:
    stage = await db.scalar(select(Stage).where(Stage.order_idx == stage_order))
    if stage is None:
        return False
    item_ids = (
        await db.scalars(select(LearnItem.id).where(LearnItem.stage_id == stage.id))
    ).all()
    if not item_ids:
        return False
    done = (
        await db.scalars(
            select(ItemProgress.item_id).where(
                ItemProgress.user_id == uid, ItemProgress.item_id.in_(item_ids)
            )
        )
    ).all()
    return len(set(done)) >= len(set(item_ids))


async def _condition_met(db: AsyncSession, uid: int, cond: dict[str, Any]) -> bool:
    """Evaluate a single achievement condition against durable data. Unknown
    condition families return False (they simply won't unlock yet)."""
    event = cond.get("event")
    need = int(cond.get("count", 1))

    if event == "item_done":
        if cond.get("item"):
            row = await db.scalar(select(LearnItem).where(LearnItem.slug == cond["item"]))
            if row is None:
                return False
            return await db.get(ItemProgress, (uid, row.id)) is not None
        if cond.get("hour_range"):
            return False  # time-of-day cosmetics: not tracked durably yet
        return await _count_items_done(db, uid) >= need
    if event == "drill_done":
        return await _count_items_done(db, uid, ItemKind.DRILL) >= need
    if event == "stage_done":
        return await _stage_done(db, uid, int(cond["stage_order"]))
    if event == "all_lessons_done":
        total = await db.scalar(
            select(func.count()).select_from(LearnItem).where(
                LearnItem.kind == ItemKind.LESSON, LearnItem.published.is_(True)
            )
        )
        done = await _count_items_done(db, uid, ItemKind.LESSON)
        return total is not None and total > 0 and done >= total
    if event == "game_win":
        if cond.get("comeback"):
            return False
        return await _game_wins(db, uid, **cond) >= need
    if event == "games_played":
        n = await db.scalar(
            select(func.count()).select_from(Game).where(
                ((Game.white_id == uid) | (Game.black_id == uid)) & Game.result.isnot(None)
            )
        )
        return int(n or 0) >= need
    if event == "bot_beaten":
        lvl = int(cond["bot_level"])
        n = await db.scalar(
            select(func.count()).select_from(Game).where(
                Game.mode == GameMode.BOT,
                Game.white_id == uid,
                Game.result == GameResult.WHITE,
                Game.bot_level >= lvl,
            )
        )
        return int(n or 0) >= 1
    if event == "duel_win":
        rows = (
            await db.scalars(
                select(DuelMatch).where(
                    (DuelMatch.player_a_id == uid) | (DuelMatch.player_b_id == uid)
                )
            )
        ).all()
        wins = sum(
            1
            for d in rows
            if (d.player_a_id == uid and d.score_a > d.score_b)
            or (d.player_b_id == uid and d.score_b > d.score_a)
        )
        return wins >= need
    if event == "streak":
        streak = await db.get(Streak, uid)
        return streak is not None and streak.current >= need
    if event == "level":
        return level_for_xp(await total_xp(db, uid)) >= need
    return False


async def evaluate_achievements(db: AsyncSession, uid: int) -> list[dict[str, Any]]:
    """Unlock any newly-satisfied achievements. Returns the freshly unlocked."""
    achievements = (await db.scalars(select(Achievement))).all()
    unlocked_ids = set(
        (
            await db.scalars(
                select(UserAchievement.achievement_id).where(UserAchievement.user_id == uid)
            )
        ).all()
    )
    fresh: list[dict[str, Any]] = []
    for ach in achievements:
        if ach.id in unlocked_ids:
            continue
        if await _condition_met(db, uid, ach.condition_json):
            db.add(
                UserAchievement(user_id=uid, achievement_id=ach.id, unlocked_at=now_utc())
            )
            await _award_xp(db, uid, ach.xp, "achievement", ach.slug)
            fresh.append({"slug": ach.slug, "title": ach.title, "icon": ach.icon, "xp": ach.xp})
    return fresh


async def on_event(
    db: AsyncSession, user_id: int, event: str, ref: str | None = None
) -> dict[str, Any]:
    """Single entrypoint: award base XP, bump the streak, re-check achievements.
    Commits. Returns a summary for the client (XP gained, level, unlocks)."""
    before_xp = await total_xp(db, user_id)
    before_level = level_for_xp(before_xp)

    base = XP.get(event, 0)
    if base:
        await _award_xp(db, user_id, base, event, ref)

    current, is_new_day = await touch_streak(db, user_id)
    if is_new_day:
        await _award_xp(db, user_id, XP["streak_day"], "streak_day", str(current))

    await db.flush()
    unlocked = await evaluate_achievements(db, user_id)
    await db.commit()

    after_xp = await total_xp(db, user_id)
    after_level = level_for_xp(after_xp)
    return {
        "xp_gained": after_xp - before_xp,
        "total_xp": after_xp,
        "level": after_level,
        "leveled_up": after_level > before_level,
        "streak": current,
        "unlocked": unlocked,
    }
