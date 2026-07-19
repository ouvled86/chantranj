"""Games REST: create bot games (Arena/Learn) + history. Live play speaks WebSocket."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError
from app.models import Game, GameMode
from app.services import games as game_service
from app.ws.game import on_game_over

router = APIRouter(prefix="/games", tags=["games"])


class TimeControlIn(BaseModel):
    base_min: float | None = Field(default=None, ge=0.01, le=180)
    inc_sec: int = Field(default=0, ge=0, le=60)


class CreateBotGameIn(BaseModel):
    bot_level: int = Field(ge=1, le=8)
    coach_level: int | None = Field(default=None, ge=1, le=5)  # set → LEARN mode
    time_control: TimeControlIn = TimeControlIn()
    rated: bool = True  # Arena only; Learn games are never rated


@router.post("", status_code=201)
async def create_bot_game(data: CreateBotGameIn, user: CurrentUser) -> dict[str, int]:
    """Human plays white vs the engine. Attach via /ws/game + game:rejoin."""
    mode = GameMode.LEARN if data.coach_level is not None else GameMode.BOT
    game = await game_service.create_game(
        white_id=user.id,
        black_id=None,
        rated=data.rated and mode == GameMode.BOT,
        base_min=data.time_control.base_min,
        inc_sec=data.time_control.inc_sec,
        mode=mode,
        bot_level=data.bot_level,
        coach_level=data.coach_level,
        on_over=on_game_over,
    )
    return {"game_id": game.id}


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


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: int
    moves_analysis: list[Any]
    accuracy_w: float | None
    accuracy_b: float | None
    generated_at: datetime


def _broker_reachable() -> bool:
    from app.workers.celery_app import celery

    try:
        with celery.connection_for_write() as conn:
            conn.ensure_connection(max_retries=0, timeout=2)
        return True
    except Exception:  # noqa: BLE001 — any broker trouble → inline fallback
        return False


@router.post("/{game_id}/review", status_code=202)
async def request_review(game_id: int, user: CurrentUser, db: DbDep) -> dict[str, str]:
    from app.models import GameReview
    from app.workers.tasks import generate_review, generate_review_async

    row = await db.get(Game, game_id)
    if row is None:
        raise AppError(404, "not_found", "No such game")
    if user.id not in (row.white_id, row.black_id):
        raise AppError(403, "forbidden", "Only players can request a review")
    if row.result is None:
        raise AppError(409, "not_finished", "Finish the game first")
    if await db.get(GameReview, game_id) is not None:
        return {"status": "ready"}
    if _broker_reachable():
        generate_review.delay(game_id)
        return {"status": "queued"}
    # No broker (SQLite/no-Redis dev): do it inline so the feature still works.
    ok = await generate_review_async(game_id)
    return {"status": "ready" if ok else "failed"}


@router.get("/{game_id}/review")
async def get_review(game_id: int, user: CurrentUser, db: DbDep) -> ReviewOut:
    from app.models import GameReview

    review = await db.get(GameReview, game_id)
    if review is None:
        raise AppError(404, "no_review", "No review yet — request one first")
    return ReviewOut.model_validate(review)
