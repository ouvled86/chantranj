"""Puzzle bank for the Duel mode.

Derived from the v1 drill positions (already legality-validated), so the whole
bank is trustworthy without a giant external import. difficulty is assigned by
theme/stage so rating-banded selection has a spread. The Lichess CSV import
(TASKS 2.7) can extend this later without schema changes.
"""

from typing import Any

# slug -> (difficulty, themes). Anything not listed is skipped.
_META: dict[str, tuple[int, list[str]]] = {
    "backrank": (800, ["back-rank", "mate"]),
    "fork": (1000, ["fork"]),
    "pin": (1100, ["pin"]),
    "skewer": (1200, ["skewer"]),
    "discovered": (1400, ["discovered-attack"]),
    "deflection": (1600, ["deflection"]),
    "smothered": (1800, ["smothered", "mate"]),
    "damiano": (1500, ["sacrifice", "mate"]),
    "oppo-drill": (1000, ["endgame", "opposition"]),
    "square-rule": (1100, ["endgame", "pawn"]),
    "skewer-race": (1500, ["endgame", "skewer"]),
    "defend": (1600, ["defense", "calculation"]),
    "anastasia": (1900, ["mate", "sacrifice", "calculation"]),
}


def puzzles_from_modules(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for module in modules:
        for item in module["items"]:
            meta = _META.get(item["id"])
            if meta is None or item.get("kind") != "puzzle" or not item.get("line"):
                continue
            difficulty, themes = meta
            out.append(
                {
                    "slug": item["id"],
                    "fen": item.get("fen"),
                    "line": item["line"],  # full line; even indices = solver's moves
                    "themes": themes,
                    "difficulty": difficulty,
                }
            )
    return out
