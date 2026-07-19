"""Celery tasks — post-game engine review (the heavy batch lane)."""

import asyncio

import structlog

from app.workers.celery_app import celery

log = structlog.get_logger()


async def generate_review_async(game_id: int) -> bool:
    """Idempotent: returns True if a review exists when we're done."""
    from app.chess import engine_client
    from app.db.session import get_session_factory
    from app.models import Game, GameReview

    async with get_session_factory()() as db:
        if await db.get(GameReview, game_id) is not None:
            return True
        game = await db.get(Game, game_id)
        if game is None or not game.pgn or game.result is None:
            return False
        data = await engine_client.review(game.pgn)
        db.add(
            GameReview(
                game_id=game_id,
                moves_analysis=data["moves"],
                accuracy_w=data["accuracy_w"],
                accuracy_b=data["accuracy_b"],
            )
        )
        await db.commit()
        log.info(
            "review_generated",
            game_id=game_id,
            accuracy_w=data["accuracy_w"],
            accuracy_b=data["accuracy_b"],
        )
        return True


@celery.task(name="review.generate")
def generate_review(game_id: int) -> None:
    asyncio.run(generate_review_async(game_id))
