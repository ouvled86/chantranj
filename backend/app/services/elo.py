"""Elo: K=40 while provisional (<30 games), K=20 after. Applied atomically at game end."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Rating, RatingMode


def expected_score(own: int, opponent: int) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent - own) / 400.0))


def k_factor(games: int) -> int:
    return 40 if games < 30 else 20


def delta(own: int, opponent: int, score: float, games: int) -> int:
    return round(k_factor(games) * (score - expected_score(own, opponent)))


async def get_or_create_rating(db: AsyncSession, user_id: int, mode: RatingMode) -> Rating:
    rating = await db.get(Rating, (user_id, mode))
    if rating is None:
        rating = Rating(user_id=user_id, mode=mode)
        db.add(rating)
        await db.flush()
    return rating


async def apply_result(
    db: AsyncSession,
    mode: RatingMode,
    white_id: int,
    black_id: int,
    white_score: float,  # 1 win, 0.5 draw, 0 loss
) -> tuple[int, int]:
    """Returns (delta_white, delta_black). Caller commits."""
    white = await get_or_create_rating(db, white_id, mode)
    black = await get_or_create_rating(db, black_id, mode)
    dw = delta(white.value, black.value, white_score, white.games)
    db_ = delta(black.value, white.value, 1.0 - white_score, black.games)
    white.value += dw
    black.value += db_
    white.games += 1
    black.games += 1
    return dw, db_
