"""Telemetry writers — append rows to the (hyper)tables. Best-effort by design:
a telemetry hiccup must never break a live game, so failures are logged, not raised."""

from typing import Any

import structlog

from app.db.session import get_session_factory
from app.models.telemetry import activity_events, move_events, rating_history

log = structlog.get_logger()


async def _insert(table: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    try:
        async with get_session_factory()() as db:
            await db.execute(table.insert(), rows)
            await db.commit()
    except Exception:  # noqa: BLE001
        log.warning("telemetry_write_failed", table=str(table.name), rows=len(rows))


async def record_move(
    *,
    game_id: int,
    user_id: int | None,
    ply: int,
    side: str,
    uci: str,
    san: str,
    clock_ms: int | None,
) -> None:
    await _insert(
        move_events,
        [
            {
                "game_id": game_id,
                "user_id": user_id,
                "ply": ply,
                "side": side,
                "uci": uci,
                "san": san,
                "clock_ms": clock_ms,
            }
        ],
    )


async def record_rating(
    *, user_id: int, mode: str, value: int, delta: int, game_id: int | None
) -> None:
    await _insert(
        rating_history,
        [{"user_id": user_id, "mode": mode, "value": value, "delta": delta, "game_id": game_id}],
    )


async def record_activity(*, user_id: int, kind: str) -> None:
    await _insert(activity_events, [{"user_id": user_id, "kind": kind}])
