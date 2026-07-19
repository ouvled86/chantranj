"""Idempotent seeding: curriculum (validated), achievements, dev fixtures."""

import json
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.seed.achievements import ACHIEVEMENTS
from app.db.seed.stage_map import STAGES, V1_PLACEMENT
from app.db.seed.validate import validate_modules
from app.db.session import get_session_factory
from app.models import Achievement, ItemKind, LearnItem, Role, Stage, User

log = structlog.get_logger()

DATA_DIR = Path(__file__).parent / "data"


def load_v1_modules() -> list[dict[str, Any]]:
    with open(DATA_DIR / "curriculum_v1.json", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


async def seed_curriculum(db: AsyncSession) -> None:
    modules = load_v1_modules()
    errors = validate_modules(modules)
    if errors:
        raise RuntimeError(f"content validation failed ({len(errors)}):\n" + "\n".join(errors))

    stage_ids: dict[str, int] = {}
    for spec in STAGES:
        stage = await db.scalar(select(Stage).where(Stage.slug == spec["slug"]))
        if stage is None:
            stage = Stage(**spec)
            db.add(stage)
            await db.flush()
        else:
            stage.title = spec["title"]
            stage.intro = spec["intro"]
            stage.order_idx = spec["order_idx"]
        stage_ids[spec["slug"]] = stage.id

    placed = 0
    for module in modules:
        for item in module["items"]:
            placement = V1_PLACEMENT.get(item["id"])
            if placement is None:
                log.warning("seed_item_unplaced", item=item["id"])
                continue
            stage_slug, order_idx = placement
            row = await db.scalar(select(LearnItem).where(LearnItem.slug == item["id"]))
            kind = ItemKind.LESSON if item["kind"] == "lesson" else ItemKind.DRILL
            if row is None:
                row = LearnItem(slug=item["id"], stage_id=stage_ids[stage_slug], kind=kind)
                db.add(row)
            row.stage_id = stage_ids[stage_slug]
            row.kind = kind
            row.title = item["title"]
            row.sub = item.get("sub") or ""
            row.order_idx = order_idx
            row.content_json = item
            row.published = True
            placed += 1
    await db.commit()
    log.info("seed_curriculum_done", stages=len(STAGES), items=placed)


async def seed_achievements(db: AsyncSession) -> None:
    for spec in ACHIEVEMENTS:
        row = await db.scalar(select(Achievement).where(Achievement.slug == spec["slug"]))
        if row is None:
            row = Achievement(slug=spec["slug"])
            db.add(row)
        row.title = spec["title"]
        row.description = spec["description"]
        row.icon = spec["icon"]
        row.category = spec["category"]
        row.condition_json = spec["condition_json"]
        row.xp = spec["xp"]
    await db.commit()
    log.info("seed_achievements_done", count=len(ACHIEVEMENTS))


DEV_USERS = [
    ("admin", "admin@study.dev", Role.ADMIN),
    ("magnus_dev", "magnus@study.dev", Role.USER),
    ("hikaru_dev", "hikaru@study.dev", Role.USER),
    ("judit_dev", "judit@study.dev", Role.USER),
    ("mikhail_dev", "mikhail@study.dev", Role.USER),
    ("vera_dev", "vera@study.dev", Role.USER),
]


async def seed_dev_fixtures(db: AsyncSession) -> None:
    """Demo accounts (password: Passw0rd1) — dev environment only."""
    pw = hash_password("Passw0rd1")
    for username, email, role in DEV_USERS:
        row = await db.scalar(select(User).where(User.username == username))
        if row is None:
            db.add(User(username=username, email=email, role=role, password_hash=pw))
    await db.commit()
    log.info("seed_dev_fixtures_done", users=len(DEV_USERS))


async def seed_all() -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        # No-Docker local dev: ensure schema exists (postgres uses Alembic).
        import app.models  # noqa: F401
        from app.db.base import Base
        from app.db.session import get_engine

        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with get_session_factory()() as db:
        await seed_curriculum(db)
        await seed_achievements(db)
        if settings.env == "dev":
            await seed_dev_fixtures(db)
    log.info("seed_all_done", env=settings.env)
