"""XP/levels/streaks + achievement unlocking wired through real endpoints."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.seed.run import seed_all
from app.services import gamification


@pytest.fixture(autouse=True)
def _seeded(client: TestClient) -> None:
    asyncio.run(seed_all())


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token") or ""}


def test_level_curve_monotonic() -> None:
    assert gamification.level_for_xp(0) == 1
    assert gamification.level_for_xp(50) == 1
    assert gamification.level_for_xp(100) == 2
    # thresholds strictly increase and round-trip
    prev = -1
    for n in range(1, 30):
        need = gamification.xp_for_level(n)
        assert need > prev
        assert gamification.level_for_xp(need) >= n
        prev = need


def test_completing_lesson_awards_xp_and_first_steps_achievement(
    client: TestClient, registered: dict[str, str]
) -> None:
    # Complete the first available item (kq-mate lesson).
    r = client.post("/api/v1/learn/items/kq-mate/complete", headers=_csrf(client))
    assert r.status_code == 200
    reward = r.json()["reward"]
    assert reward is not None
    assert reward["xp_gained"] >= 20  # item XP + streak-day bonus
    slugs = [u["slug"] for u in reward["unlocked"]]
    assert "first-steps" in slugs  # first item done

    # Replaying grants no second reward.
    r2 = client.post("/api/v1/learn/items/kq-mate/complete", headers=_csrf(client))
    assert r2.json()["reward"] is None

    stats = client.get("/api/v1/users/me/stats").json()
    assert stats["total_xp"] == reward["total_xp"]
    assert stats["items_done"] == 1
    assert stats["achievements_unlocked"] >= 1
    assert stats["streak"] == 1


def test_achievements_endpoint_reflects_unlocks(
    client: TestClient, registered: dict[str, str]
) -> None:
    before = client.get("/api/v1/achievements").json()
    assert len(before) == 40
    assert all(not a["unlocked"] for a in before)

    client.post("/api/v1/learn/items/kq-mate/complete", headers=_csrf(client))
    after = client.get("/api/v1/achievements").json()
    first = next(a for a in after if a["slug"] == "first-steps")
    assert first["unlocked"] and first["unlocked_at"]
    # sorted: unlocked before locked within a category
    learning = [a for a in after if a["category"] == "learning"]
    assert learning[0]["unlocked"]


def test_streak_increments_across_days(
    client: TestClient, registered: dict[str, str]
) -> None:
    async def run() -> tuple[int, int]:
        from datetime import timedelta

        from sqlalchemy import select

        from app.core.security import now_utc
        from app.db.session import get_session_factory
        from app.models import Streak, User

        async with get_session_factory()() as db:
            uid = (await db.scalar(select(User).where(User.username == registered["username"]))).id
            s1, _ = await gamification.touch_streak(db, uid)
            # simulate that activity was yesterday, then touch again
            streak = await db.get(Streak, uid)
            streak.last_active_date = now_utc().date() - timedelta(days=1)
            await db.commit()
            s2, new_day = await gamification.touch_streak(db, uid)
            return s1, s2

    first, second = asyncio.run(run())
    assert first == 1
    assert second == 2


def test_achievement_counts_are_user_scoped(client: TestClient) -> None:
    """One user completing a drill must not unlock another user's drill badge."""

    async def scenario() -> tuple[bool, bool]:
        from sqlalchemy import select

        from app.core.security import now_utc
        from app.db.session import get_session_factory
        from app.models import ItemKind, ItemProgress, LearnItem, UserAchievement
        from app.models.user import User

        async with get_session_factory()() as db:
            a = User(email="a@t.dev", username="ua", password_hash="x")
            b = User(email="b@t.dev", username="ub", password_hash="x")
            db.add_all([a, b])
            await db.flush()
            drill = await db.scalar(select(LearnItem).where(LearnItem.kind == ItemKind.DRILL))
            assert drill is not None
            db.add(ItemProgress(user_id=a.id, item_id=drill.id, completed_at=now_utc()))
            await db.commit()

            await gamification.evaluate_achievements(db, a.id)
            await gamification.evaluate_achievements(db, b.id)

            async def has(uid: int) -> bool:
                from app.models import Achievement

                fb = await db.scalar(select(Achievement).where(Achievement.slug == "first-blood"))
                return (
                    await db.get(UserAchievement, (uid, fb.id)) is not None if fb else False
                )

            return await has(a.id), await has(b.id)

    a_has, b_has = asyncio.run(scenario())
    assert a_has is True  # A solved a drill
    assert b_has is False  # B did nothing — must stay locked


def test_stats_shape(client: TestClient, registered: dict[str, str]) -> None:
    s = client.get("/api/v1/users/me/stats").json()
    assert s["level"] == 1 and s["total_xp"] == 0
    assert set(s["ratings"]) == {"online", "bot", "duel"}
    assert s["achievements_total"] == 40
    assert s["xp_for_next"] > 0
