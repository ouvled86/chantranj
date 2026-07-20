from typing import Any

from pydantic import BaseModel

from app.models.curriculum import ItemKind


class ItemSummary(BaseModel):
    slug: str
    kind: ItemKind
    title: str
    sub: str
    order_idx: int
    status: str  # DONE | AVAILABLE | LOCKED


class StageOut(BaseModel):
    slug: str
    title: str
    intro: str
    order_idx: int
    items: list[ItemSummary]


class ItemDetail(BaseModel):
    slug: str
    kind: ItemKind
    title: str
    sub: str
    status: str
    content: dict[str, Any]
    boss: dict[str, Any] | None = None  # boss_config for BOSS items (no bot secrets here)
