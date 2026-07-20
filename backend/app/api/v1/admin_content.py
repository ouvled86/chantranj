"""Admin CMS — author/edit/reorder/publish curriculum content.

Publishing is gated by the same python-chess validator that guards seeding:
invalid chess content can never reach learners, whether it comes from a seed
file or the admin editor.
"""

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbDep, audit
from app.core.errors import AppError
from app.db.seed.validate import validate_bosses, validate_item
from app.models import ItemKind, LearnItem, Stage

router = APIRouter(prefix="/admin", tags=["admin-cms"])


# ---------- schemas ----------

class StageIn(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=120)
    intro: str = ""
    order_idx: int
    published: bool = True


class StagePatch(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    intro: str | None = None
    order_idx: int | None = None
    published: bool | None = None


class StageOut(BaseModel):
    id: int
    slug: str
    title: str
    intro: str
    order_idx: int
    published: bool
    item_count: int


class ItemIn(BaseModel):
    stage_id: int
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    kind: ItemKind
    title: str = Field(min_length=1, max_length=120)
    sub: str = ""
    order_idx: int
    content_json: dict[str, Any] = Field(default_factory=dict)
    boss_config: dict[str, Any] | None = None


class ItemPatch(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    sub: str | None = None
    order_idx: int | None = None
    content_json: dict[str, Any] | None = None
    boss_config: dict[str, Any] | None = None


class ItemOut(BaseModel):
    id: int
    stage_id: int
    slug: str
    kind: ItemKind
    title: str
    sub: str
    order_idx: int
    published: bool
    version: int


class ItemFull(ItemOut):
    content_json: dict[str, Any]
    boss_config: dict[str, Any] | None


class ReorderIn(BaseModel):
    stage_id: int
    ordered_slugs: list[str]


class ValidationOut(BaseModel):
    valid: bool
    errors: list[str]


# ---------- content validation ----------

def _validate_content(item: LearnItem) -> list[str]:
    """Run the chess validator against an item's stored content."""
    if item.kind == ItemKind.BOSS:
        cfg = item.boss_config or {}
        return validate_bosses(
            [{"slug": item.slug, "boss_config": {
                "bot_level": cfg.get("bot_level", 1),
                "start_fen": cfg.get("start_fen"),
            }}]
        )
    payload = dict(item.content_json)
    payload.setdefault("id", item.slug)
    return validate_item(payload)


# ---------- stages ----------

@router.get("/stages")
async def list_stages(admin: AdminUser, db: DbDep) -> list[StageOut]:
    stages = (await db.scalars(select(Stage).order_by(Stage.order_idx))).all()
    out: list[StageOut] = []
    for s in stages:
        count = await db.scalar(
            select(func.count()).select_from(LearnItem).where(LearnItem.stage_id == s.id)
        )
        out.append(
            StageOut(
                id=s.id, slug=s.slug, title=s.title, intro=s.intro,
                order_idx=s.order_idx, published=s.published, item_count=count or 0,
            )
        )
    return out


@router.post("/stages", status_code=201)
async def create_stage(data: StageIn, admin: AdminUser, request: Request, db: DbDep) -> StageOut:
    if await db.scalar(select(Stage).where(Stage.slug == data.slug)):
        raise AppError(409, "already_exists", "A stage with that slug exists")
    stage = Stage(**data.model_dump())
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    await audit(db, request, admin.id, "cms.stage_create", target=data.slug)
    return StageOut(**data.model_dump(), id=stage.id, item_count=0)


@router.patch("/stages/{stage_id}")
async def patch_stage(
    stage_id: int, data: StagePatch, admin: AdminUser, request: Request, db: DbDep
) -> StageOut:
    stage = await db.get(Stage, stage_id)
    if stage is None:
        raise AppError(404, "not_found", "No such stage")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(stage, field, value)
    await db.commit()
    await db.refresh(stage)
    await audit(db, request, admin.id, "cms.stage_patch", target=stage.slug)
    count = await db.scalar(
        select(func.count()).select_from(LearnItem).where(LearnItem.stage_id == stage.id)
    )
    return StageOut(
        id=stage.id, slug=stage.slug, title=stage.title, intro=stage.intro,
        order_idx=stage.order_idx, published=stage.published, item_count=count or 0,
    )


# ---------- items ----------

@router.get("/items")
async def list_items(
    admin: AdminUser, db: DbDep, stage_id: int | None = Query(default=None)
) -> list[ItemOut]:
    stmt = select(LearnItem)
    if stage_id is not None:
        stmt = stmt.where(LearnItem.stage_id == stage_id)
    rows = (await db.scalars(stmt.order_by(LearnItem.stage_id, LearnItem.order_idx))).all()
    return [ItemOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/items/{item_id}")
async def get_item(item_id: int, admin: AdminUser, db: DbDep) -> ItemFull:
    item = await db.get(LearnItem, item_id)
    if item is None:
        raise AppError(404, "not_found", "No such item")
    return ItemFull.model_validate(item, from_attributes=True)


@router.post("/items", status_code=201)
async def create_item(data: ItemIn, admin: AdminUser, request: Request, db: DbDep) -> ItemFull:
    if await db.scalar(select(LearnItem).where(LearnItem.slug == data.slug)):
        raise AppError(409, "already_exists", "An item with that slug exists")
    if await db.get(Stage, data.stage_id) is None:
        raise AppError(400, "bad_stage", "No such stage")
    item = LearnItem(**data.model_dump(), published=False, version=1)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await audit(db, request, admin.id, "cms.item_create", target=data.slug)
    return ItemFull.model_validate(item, from_attributes=True)


@router.patch("/items/{item_id}")
async def patch_item(
    item_id: int, data: ItemPatch, admin: AdminUser, request: Request, db: DbDep
) -> ItemFull:
    item = await db.get(LearnItem, item_id)
    if item is None:
        raise AppError(404, "not_found", "No such item")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    await audit(db, request, admin.id, "cms.item_patch", target=item.slug)
    return ItemFull.model_validate(item, from_attributes=True)


@router.post("/items/{item_id}/validate")
async def validate_item_content(item_id: int, admin: AdminUser, db: DbDep) -> ValidationOut:
    item = await db.get(LearnItem, item_id)
    if item is None:
        raise AppError(404, "not_found", "No such item")
    errors = _validate_content(item)
    return ValidationOut(valid=not errors, errors=errors)


@router.post("/items/{item_id}/publish")
async def publish_item(
    item_id: int, admin: AdminUser, request: Request, db: DbDep
) -> ItemFull:
    item = await db.get(LearnItem, item_id)
    if item is None:
        raise AppError(404, "not_found", "No such item")
    errors = _validate_content(item)
    if errors:
        raise AppError(422, "invalid_content", "Cannot publish invalid content", details=errors)
    item.published = True
    item.version += 1
    await db.commit()
    await db.refresh(item)
    await audit(db, request, admin.id, "cms.item_publish", target=item.slug, version=item.version)
    return ItemFull.model_validate(item, from_attributes=True)


@router.post("/items/{item_id}/unpublish")
async def unpublish_item(
    item_id: int, admin: AdminUser, request: Request, db: DbDep
) -> ItemFull:
    item = await db.get(LearnItem, item_id)
    if item is None:
        raise AppError(404, "not_found", "No such item")
    item.published = False
    await db.commit()
    await db.refresh(item)
    await audit(db, request, admin.id, "cms.item_unpublish", target=item.slug)
    return ItemFull.model_validate(item, from_attributes=True)


@router.post("/items/reorder")
async def reorder_items(
    data: ReorderIn, admin: AdminUser, request: Request, db: DbDep
) -> dict[str, str]:
    rows = (
        await db.scalars(select(LearnItem).where(LearnItem.stage_id == data.stage_id))
    ).all()
    by_slug = {r.slug: r for r in rows}
    for idx, slug in enumerate(data.ordered_slugs, start=1):
        if slug in by_slug:
            by_slug[slug].order_idx = idx
    await db.commit()
    await audit(db, request, admin.id, "cms.reorder", target=str(data.stage_id))
    return {"status": "ok"}


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, admin: AdminUser, request: Request, db: DbDep) -> None:
    item = await db.get(LearnItem, item_id)
    if item is None:
        raise AppError(404, "not_found", "No such item")
    slug = item.slug
    await db.delete(item)
    await db.commit()
    await audit(db, request, admin.id, "cms.item_delete", target=slug)
