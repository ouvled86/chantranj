"""Learn-by-Playing coaching — the L1-L5 assistance ladder (docs/PLAN.md §3).

One code path, config-driven. All engine math mirrors the review endpoint:
win% model + drop thresholds, so live tags and post-game tags agree.
"""

import math
from typing import Any, TypedDict

import structlog

from app.chess import engine_client
from app.chess.engine_client import EngineUnavailable

log = structlog.get_logger()

COACH_DEPTH = 10
PREMOVE_DEPTH = 8


class CoachConfig(TypedDict):
    name: str
    eval_bar: str  # always | on_demand | off
    hints: int | None  # None = unlimited, 0 = none
    takebacks: int | None  # None = unlimited, 0 = none
    feedback: str  # explained | tags | own_tags | blunder_alert | critical_ping
    blunder_confirm: bool


COACH_LEVELS: dict[int, CoachConfig] = {
    1: {"name": "Full Coach", "eval_bar": "always", "hints": None, "takebacks": None,
        "feedback": "explained", "blunder_confirm": True},
    2: {"name": "Guided", "eval_bar": "always", "hints": 5, "takebacks": 3,
        "feedback": "tags", "blunder_confirm": False},
    3: {"name": "Balanced", "eval_bar": "on_demand", "hints": 3, "takebacks": 1,
        "feedback": "own_tags", "blunder_confirm": False},
    4: {"name": "Whisper", "eval_bar": "off", "hints": 0, "takebacks": 0,
        "feedback": "blunder_alert", "blunder_confirm": False},
    5: {"name": "Shadow", "eval_bar": "off", "hints": 0, "takebacks": 0,
        "feedback": "critical_ping", "blunder_confirm": False},
}

TAG_EXPLANATIONS = {
    "great": "Excellent — that keeps every promise of the position.",
    "good": "A sound move.",
    "inaccuracy": "Playable, but something stronger was available.",
    "mistake": "That concedes real ground — compare it with the best move.",
    "blunder": "That loses material or the game — take it back and look again.",
}


def win_pct(cp: int) -> float:
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def tag_from_drop(drop: float) -> str:
    if drop >= 20:
        return "blunder"
    if drop >= 10:
        return "mistake"
    if drop >= 5:
        return "inaccuracy"
    if drop <= 0.5:
        return "great"
    return "good"


async def evaluate(fen: str, depth: int = COACH_DEPTH) -> int | None:
    """White-POV centipawns, mates folded to ±10000. None if engine down/game over."""
    try:
        lines = await engine_client.analyse(fen, depth=depth)
    except EngineUnavailable:
        log.warning("coach_eval_unavailable")
        return None
    if not lines:
        return None
    line = lines[0]
    if line.get("mate") is not None:
        return 10_000 if int(line["mate"]) > 0 else -10_000
    cp = line.get("eval_cp")
    return int(cp) if cp is not None else None


async def best_move(fen: str, depth: int = COACH_DEPTH) -> str | None:
    try:
        lines = await engine_client.analyse(fen, depth=depth)
    except EngineUnavailable:
        return None
    return str(lines[0]["move"]) if lines and lines[0].get("move") else None


def build_info(
    level: int,
    *,
    ply: int,
    eval_cp: int | None,
    drop: float | None,
    hints_left: int | None,
    takebacks_left: int | None,
) -> dict[str, Any]:
    """Filter raw analysis into what this coach level is allowed to reveal.
    The human plays WHITE in Learn games; drop is from white's perspective."""
    cfg = COACH_LEVELS[level]
    info: dict[str, Any] = {
        "ply": ply,
        "level": level,
        "hints_left": hints_left,
        "takebacks_left": takebacks_left,
    }
    if cfg["eval_bar"] in ("always", "on_demand") and eval_cp is not None:
        info["eval_cp"] = eval_cp

    if drop is None:
        return info
    tag = tag_from_drop(drop)
    feedback = cfg["feedback"]
    if feedback == "explained":
        info["tag"] = tag
        info["note"] = TAG_EXPLANATIONS[tag]
    elif feedback in ("tags", "own_tags"):
        info["tag"] = tag
    elif feedback == "blunder_alert":
        if tag in ("mistake", "blunder"):
            info["tag"] = tag
    elif feedback == "critical_ping":
        if abs(drop) >= 15:
            info["critical"] = True
    return info
