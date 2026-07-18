"""Content validator: replay every lesson step and drill line with python-chess.

Seeding refuses to run if any position or move is illegal — bad chess content
must never reach users.
"""

from typing import Any

import chess

START = chess.STARTING_FEN


def _try_board(fen: str, where: str, errors: list[str]) -> chess.Board | None:
    try:
        return chess.Board(fen)
    except ValueError as exc:
        errors.append(f"{where}: bad FEN {fen!r} ({exc})")
        return None


def validate_item(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    slug = item["id"]
    board = _try_board(item.get("fen") or START, f"{slug}:start", errors)
    if board is None:
        return errors

    if item.get("steps"):
        for i, step in enumerate(item["steps"]):
            where = f"{slug}:step[{i}]"
            if step.get("fen"):
                nxt = _try_board(step["fen"], where, errors)
                if nxt is None:
                    continue
                board = nxt
            if step.get("move"):
                try:
                    board.push_uci(step["move"])
                except ValueError as exc:
                    errors.append(f"{where}: illegal move {step['move']!r} ({exc})")

    if item.get("line"):
        for i, entry in enumerate(item["line"]):
            try:
                board.push_uci(entry["move"])
            except ValueError as exc:
                errors.append(f"{slug}:line[{i}]: illegal move {entry['move']!r} ({exc})")

    return errors


def validate_modules(modules: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for module in modules:
        for item in module["items"]:
            errors.extend(validate_item(item))
    return errors
