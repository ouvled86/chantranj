"""HTTP client for the engine service + engine_samples telemetry around calls."""

import time
from typing import Any

import httpx
import structlog

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.telemetry import engine_samples

log = structlog.get_logger()

# Anchor Elo per bot level — used when rating human vs bot (Arena).
BOT_ANCHOR_RATING = {1: 600, 2: 800, 3: 1000, 4: 1200, 5: 1400, 6: 1700, 7: 2000, 8: 2300}


class EngineUnavailable(Exception):
    pass


async def _post(path: str, payload: dict[str, Any], kind: str, timeout_s: float) -> dict[str, Any]:
    settings = get_settings()
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=settings.engine_url, timeout=timeout_s) as client:
            resp = await client.post(path, json=payload)
    except httpx.HTTPError as exc:
        raise EngineUnavailable(f"engine {path} unreachable: {exc}") from exc
    latency_ms = (time.monotonic() - started) * 1000
    try:
        async with get_session_factory()() as db:
            await db.execute(
                engine_samples.insert(),
                [{"request_kind": kind, "latency_ms": latency_ms, "depth": payload.get("depth")}],
            )
            await db.commit()
    except Exception:  # noqa: BLE001 — telemetry must never break gameplay
        log.warning("engine_sample_write_failed")
    if resp.status_code != 200:
        raise EngineUnavailable(f"engine {path} -> {resp.status_code}: {resp.text[:200]}")
    return resp.json()  # type: ignore[no-any-return]


async def botmove(fen: str, level: int) -> str:
    data = await _post("/botmove", {"fen": fen, "level": level}, "botmove", timeout_s=15)
    return str(data["move"])


async def analyse(fen: str, depth: int = 12, multipv: int = 1) -> list[dict[str, Any]]:
    data = await _post(
        "/analyse", {"fen": fen, "depth": depth, "multipv": multipv}, "analyse", timeout_s=30
    )
    return list(data["lines"])


async def review(pgn: str, depth: int = 10) -> dict[str, Any]:
    return await _post("/review", {"pgn": pgn, "depth": depth}, "review", timeout_s=300)
