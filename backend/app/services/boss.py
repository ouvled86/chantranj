"""Boss checkpoints — end-of-stage challenges vs a bot with a verified objective.

boss_config (stored on LearnItem.boss_config) shape:
{
  "start_fen": "<fen>" | null,   # null = standard start
  "bot_level": 1-8,
  "player_color": "white" | "black",
  "objective": "win" | "checkmate" | "draw" | "convert",
  "move_limit": <int> | null,    # full moves; required for "convert"
  "time_control": {"base_min": <float>|null, "inc_sec": <int>}
}

Verification reads the FINISHED Game row (durable), never live state — so a boss
survives a server restart mid-fight and can still be judged on reconnect.
"""

import io
from typing import Any

import chess
import chess.pgn

from app.models import Game, GameResult


def bot_color(player_color: str) -> str:
    return "black" if player_color == "white" else "white"


def _plies(pgn: str) -> int:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return 0
    return sum(1 for _ in game.mainline_moves())


def verify(game: Game, config: dict[str, Any], user_id: int) -> tuple[bool, str]:
    """Returns (passed, human_readable_reason). Pure function of the game record."""
    if game.result is None:
        return False, "The game hasn't finished yet."
    if user_id not in (game.white_id, game.black_id):
        return False, "That isn't your game."

    player_color = config.get("player_color", "white")
    human_is_white = player_color == "white"
    if (human_is_white and game.white_id != user_id) or (
        not human_is_white and game.black_id != user_id
    ):
        return False, "You played the wrong colour for this challenge."

    human_won = (
        (human_is_white and game.result == GameResult.WHITE)
        or (not human_is_white and game.result == GameResult.BLACK)
    )
    is_draw = game.result == GameResult.DRAW
    objective = config.get("objective", "win")

    if game.result == GameResult.ABORTED:
        return False, "The game was aborted — try again."

    if objective in ("win", "checkmate"):
        if not human_won:
            return False, "You needed to win this one. Line up and try again."
        if objective == "checkmate" and game.end_reason != "checkmate":
            return False, "Win by checkmate specifically — no resignations or flags."
        limit = config.get("move_limit")
        if limit is not None and _plies(game.pgn) > limit * 2:
            return False, f"Deliver it within {limit} moves next time — you were close."
        return True, "Checkmate delivered. Stage cleared."

    if objective == "convert":
        if not human_won:
            return False, "Convert the advantage into a win — don't let it slip."
        limit = config.get("move_limit")
        if limit is not None and _plies(game.pgn) > limit * 2:
            return False, f"Convert within {limit} moves — tighten the technique."
        return True, "Converted cleanly. Stage cleared."

    if objective == "draw":
        if is_draw or human_won:
            return True, "You held the line. Stage cleared."
        return False, "You had to hold the draw — the fortress cracked. Try again."

    return False, "Unknown objective."
