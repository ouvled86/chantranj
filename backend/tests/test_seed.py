"""Content validator + idempotent seeding against the test database."""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.seed.run import load_v1_modules, seed_all
from app.db.seed.validate import validate_modules
from app.db.session import get_session_factory
from app.models import Achievement, LearnItem, Stage


def test_v1_content_is_fully_legal() -> None:
    modules = load_v1_modules()
    assert sum(len(m["items"]) for m in modules) == 27
    errors = validate_modules(modules)
    assert errors == [], "\n".join(errors)


def test_validator_catches_illegal_content() -> None:
    bad = [
        {
            "module": "x",
            "items": [
                {"id": "bad1", "fen": None, "steps": [{"move": "e2e5"}], "line": None},
                {"id": "bad2", "fen": "not a fen", "steps": None, "line": None},
            ],
        }
    ]
    errors = validate_modules(bad)
    assert len(errors) == 2


def test_seed_is_idempotent(client: TestClient) -> None:
    # client fixture guarantees tables exist (lifespan create_all).
    async def _counts() -> tuple[int, int, int]:
        async with get_session_factory()() as db:
            stages = await db.scalar(select(func.count()).select_from(Stage)) or 0
            items = await db.scalar(select(func.count()).select_from(LearnItem)) or 0
            achs = await db.scalar(select(func.count()).select_from(Achievement)) or 0
            return stages, items, achs

    async def _run() -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        await seed_all()
        first = await _counts()
        await seed_all()
        second = await _counts()
        return first, second

    first, second = asyncio.run(_run())
    assert first == (12, 39, 40)  # 12 stages, 27 v1 items + 12 bosses, 40 achievements
    assert second == first
