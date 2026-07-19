"""Game history (finished games live in the DB; live games speak WebSocket)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError
from app.models import Game

router = APIRouter(prefix="/games", tags=["games"])


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: str
    white_id: int | None
    black_id: int | None
    time_control: dict[str, Any]
    result: str | None
    end_reason: str | None
    rated: bool
    rating_delta_w: int | None
    rating_delta_b: int | None
    started_at: datetime
    ended_at: datetime | None


class GameDetail(GameOut):
    pgn: str
    start_fen: str | None


@router.get("")
async def list_games(
    user: CurrentUser,
    db: DbDep,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> list[GameOut]:
    rows = (
        await db.scalars(
            select(Game)
            .where(or_(Game.white_id == user.id, Game.black_id == user.id))
            .order_by(Game.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    return [GameOut.model_validate(g) for g in rows]


@router.get("/{game_id}")
async def get_game(game_id: int, user: CurrentUser, db: DbDep) -> GameDetail:
    row = await db.get(Game, game_id)
    if row is None:
        raise AppError(404, "not_found", "No such game")
    return GameDetail.model_validate(row)
