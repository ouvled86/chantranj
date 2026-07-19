"""Live game service — the server is the referee.

Every rule decision runs through python-chess here: legality, clocks, results.
Active games live in process memory (single-worker correctness); finished games
are durable in the DB. Redis-backed cross-worker fan-out is a Phase 9 concern.

Bot games (modes BOT / LEARN): the human always plays white in v1, the engine
plays black via drive_bot() — the engine call happens OUTSIDE the game lock so
a slow Stockfish can never freeze move handling.
"""

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import chess
import chess.pgn
import structlog

from app.chess import engine_client
from app.chess.engine_client import BOT_ANCHOR_RATING, EngineUnavailable
from app.core.security import now_utc
from app.db.session import get_session_factory
from app.models import Game, GameMode, GameResult, RatingMode
from app.services import elo
from app.telemetry import writer

log = structlog.get_logger()

DISCONNECT_GRACE_S = 30.0

# game_id -> LiveGame
_registry: dict[int, "LiveGame"] = {}

# Called with (game, payload) when a game ends — set by the WS layer.
OverCallback = Callable[["LiveGame", dict[str, Any]], Awaitable[None]]


@dataclass
class LiveGame:
    id: int
    white_id: int
    black_id: int | None  # None = engine opponent
    rated: bool
    base_ms: int | None  # None = untimed
    inc_ms: int = 0
    mode: GameMode = GameMode.ONLINE
    bot_level: int | None = None
    coach_level: int | None = None
    board: chess.Board = field(default_factory=chess.Board)
    white_ms: int = 0
    black_ms: int = 0
    turn_started: float = field(default_factory=time.monotonic)
    moves: list[tuple[str, str]] = field(default_factory=list)  # (uci, san)
    status: str = "active"
    draw_offer_by: int | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    timeout_task: asyncio.Task[None] | None = None
    disconnect_tasks: dict[int, asyncio.Task[None]] = field(default_factory=dict)
    on_over: OverCallback | None = None

    def player_color(self, user_id: int) -> chess.Color | None:
        if user_id == self.white_id:
            return chess.WHITE
        if self.black_id is not None and user_id == self.black_id:
            return chess.BLACK
        return None

    def clocks(self) -> dict[str, int | None]:
        if self.base_ms is None:
            return {"w": None, "b": None}
        w, b = self.white_ms, self.black_ms
        if self.status == "active":
            elapsed = int((time.monotonic() - self.turn_started) * 1000)
            if self.board.turn == chess.WHITE:
                w = max(0, w - elapsed)
            else:
                b = max(0, b - elapsed)
        return {"w": w, "b": b}

    def state_payload(self) -> dict[str, Any]:
        return {
            "game_id": self.id,
            "fen": self.board.fen(),
            "turn": "w" if self.board.turn == chess.WHITE else "b",
            "clocks": self.clocks(),
            "last_move": self.moves[-1][0] if self.moves else None,
            "moves": [{"uci": u, "san": s} for u, s in self.moves],
            "status": self.status,
            "draw_offer_by": self.draw_offer_by,
            "white_id": self.white_id,
            "black_id": self.black_id,
            "bot_level": self.bot_level,
            "coach_level": self.coach_level,
        }


def get_live(game_id: int) -> LiveGame | None:
    return _registry.get(game_id)


async def create_game(
    *,
    white_id: int,
    black_id: int | None,
    rated: bool,
    base_min: float | None,
    inc_sec: int,
    mode: GameMode = GameMode.ONLINE,
    bot_level: int | None = None,
    coach_level: int | None = None,
    on_over: OverCallback | None = None,
) -> LiveGame:
    async with get_session_factory()() as db:
        row = Game(
            mode=mode,
            white_id=white_id,
            black_id=black_id,
            bot_level=bot_level,
            coach_level=coach_level,
            rated=rated,
            time_control={"base_min": base_min, "inc_sec": inc_sec},
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

    base_ms = None if base_min is None else int(base_min * 60_000)
    game = LiveGame(
        id=row.id,
        white_id=white_id,
        black_id=black_id,
        rated=rated,
        base_ms=base_ms,
        inc_ms=inc_sec * 1000,
        mode=mode,
        bot_level=bot_level,
        coach_level=coach_level,
        white_ms=base_ms or 0,
        black_ms=base_ms or 0,
        on_over=on_over,
    )
    _registry[game.id] = game
    if base_ms is not None:
        game.timeout_task = asyncio.create_task(_watchdog(game))
    log.info(
        "game_created",
        game_id=game.id,
        mode=mode.value,
        white=white_id,
        black=black_id,
        bot_level=bot_level,
        rated=rated,
    )
    return game


class MoveError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


async def make_move(game: LiveGame, user_id: int, uci: str) -> dict[str, Any]:
    """Validate + apply a HUMAN move. Returns the broadcast payload."""
    async with game.lock:
        if game.status != "active":
            raise MoveError("game_over", "The game is finished")
        color = game.player_color(user_id)
        if color is None:
            raise MoveError("not_a_player", "You are not playing this game")
        if game.board.turn != color:
            raise MoveError("not_your_turn", "Not your turn")
        return await _apply_locked(game, uci, user_id, color)


async def play_bot_move(game: LiveGame, uci: str) -> dict[str, Any] | None:
    """Apply an engine move (bot = black). Returns None if the moment passed."""
    async with game.lock:
        if game.status != "active" or game.bot_level is None:
            return None
        if game.board.turn != chess.BLACK:
            return None
        return await _apply_locked(game, uci, None, chess.BLACK)


async def drive_bot(
    game: LiveGame, notify: Callable[[dict[str, Any]], Awaitable[None]] | None = None
) -> None:
    """Fetch + apply the engine reply if it's the bot's turn. Engine call runs
    WITHOUT the game lock; the apply step revalidates."""
    if game.bot_level is None or game.status != "active" or game.board.turn != chess.BLACK:
        return
    try:
        uci = await engine_client.botmove(game.board.fen(), game.bot_level)
    except EngineUnavailable as exc:
        log.warning("bot_move_failed", game_id=game.id, error=str(exc))
        return
    payload = await play_bot_move(game, uci)
    if payload is not None and notify is not None:
        await notify(payload)  # final position included even if the bot just mated


async def _apply_locked(
    game: LiveGame, uci: str, user_id: int | None, color: chess.Color
) -> dict[str, Any]:
    """Caller holds game.lock and has validated the mover."""
    try:
        move = chess.Move.from_uci(uci)
    except ValueError as exc:
        raise MoveError("bad_move", "Unreadable move") from exc
    # Auto-queen bare promotions arriving without a piece suffix.
    if (
        move.promotion is None
        and game.board.piece_type_at(move.from_square) == chess.PAWN
        and chess.square_rank(move.to_square) in (0, 7)
    ):
        move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
    if move not in game.board.legal_moves:
        raise MoveError("illegal", "Illegal move")

    # Clocks
    mover_clock: int | None = None
    if game.base_ms is not None:
        elapsed = int((time.monotonic() - game.turn_started) * 1000)
        if color == chess.WHITE:
            game.white_ms -= elapsed
            if game.white_ms <= 0:
                await _finish_locked(game, GameResult.BLACK, "timeout")
                return game.state_payload()
            game.white_ms += game.inc_ms
            mover_clock = game.white_ms
        else:
            game.black_ms -= elapsed
            if game.black_ms <= 0:
                await _finish_locked(game, GameResult.WHITE, "timeout")
                return game.state_payload()
            game.black_ms += game.inc_ms
            mover_clock = game.black_ms

    san = game.board.san(move)
    game.board.push(move)
    game.moves.append((move.uci(), san))
    game.turn_started = time.monotonic()
    game.draw_offer_by = None
    _reschedule_watchdog(game)

    await writer.record_move(
        game_id=game.id,
        user_id=user_id,
        ply=len(game.moves),
        side="w" if color == chess.WHITE else "b",
        uci=move.uci(),
        san=san,
        clock_ms=mover_clock,
    )

    outcome = game.board.outcome(claim_draw=True)
    if outcome is not None:
        if outcome.winner is None:
            await _finish_locked(game, GameResult.DRAW, outcome.termination.name.lower())
        else:
            await _finish_locked(
                game,
                GameResult.WHITE if outcome.winner == chess.WHITE else GameResult.BLACK,
                outcome.termination.name.lower(),
            )

    payload = game.state_payload()
    payload["san"] = san
    payload["uci"] = move.uci()
    payload["by"] = "w" if color == chess.WHITE else "b"
    return payload


async def resign(game: LiveGame, user_id: int) -> None:
    async with game.lock:
        if game.status != "active":
            return
        color = game.player_color(user_id)
        if color is None:
            raise MoveError("not_a_player", "You are not playing this game")
        winner = GameResult.BLACK if color == chess.WHITE else GameResult.WHITE
        await _finish_locked(game, winner, "resignation")


async def offer_draw(game: LiveGame, user_id: int) -> None:
    async with game.lock:
        if game.status != "active" or game.player_color(user_id) is None:
            raise MoveError("not_a_player", "Cannot offer a draw here")
        # Bots decline politely by ignoring; humans get the banner.
        game.draw_offer_by = user_id


async def respond_draw(game: LiveGame, user_id: int, accept: bool) -> bool:
    async with game.lock:
        if game.status != "active" or game.player_color(user_id) is None:
            return False
        if game.draw_offer_by is None or game.draw_offer_by == user_id:
            return False
        if accept:
            await _finish_locked(game, GameResult.DRAW, "agreement")
            return True
        game.draw_offer_by = None
        return False


async def handle_disconnect(game: LiveGame, user_id: int) -> None:
    """Start the 30s forfeit grace timer for a player who dropped."""
    if game.status != "active" or game.player_color(user_id) is None:
        return

    async def _grace() -> None:
        await asyncio.sleep(DISCONNECT_GRACE_S)
        async with game.lock:
            if game.status != "active":
                return
            if len(game.moves) < 2:
                await _finish_locked(game, GameResult.ABORTED, "abandoned")
            else:
                color = game.player_color(user_id)
                winner = GameResult.BLACK if color == chess.WHITE else GameResult.WHITE
                await _finish_locked(game, winner, "abandonment")

    _cancel(game.disconnect_tasks.pop(user_id, None))
    game.disconnect_tasks[user_id] = asyncio.create_task(_grace())


def handle_reconnect(game: LiveGame, user_id: int) -> None:
    _cancel(game.disconnect_tasks.pop(user_id, None))


def _cancel(task: asyncio.Task[None] | None) -> None:
    """Cancel a helper task — but NEVER the currently running one: the watchdog
    (or a grace task) may itself be the finisher, and self-cancellation poisons
    every await that follows (this exact bug ate game:over on flag falls)."""
    if task is not None and not task.done() and task is not asyncio.current_task():
        task.cancel()


def _reschedule_watchdog(game: LiveGame) -> None:
    if game.base_ms is None or game.status != "active":
        return
    _cancel(game.timeout_task)
    game.timeout_task = asyncio.create_task(_watchdog(game))


async def _watchdog(game: LiveGame) -> None:
    """Sleeps until the side to move would flag, then verifies and ends the game."""
    with contextlib.suppress(asyncio.CancelledError):
        while game.status == "active":
            clocks = game.clocks()
            remaining = clocks["w"] if game.board.turn == chess.WHITE else clocks["b"]
            if remaining is None:
                return
            await asyncio.sleep(remaining / 1000 + 0.02)
            async with game.lock:
                if game.status != "active":
                    return
                clocks = game.clocks()
                current = clocks["w"] if game.board.turn == chess.WHITE else clocks["b"]
                if current is not None and current <= 0:
                    loser_white = game.board.turn == chess.WHITE
                    await _finish_locked(
                        game,
                        GameResult.BLACK if loser_white else GameResult.WHITE,
                        "timeout",
                    )
                    return


async def _finish_locked(game: LiveGame, result: GameResult, reason: str) -> None:
    """Caller must hold game.lock."""
    game.status = "finished"
    _cancel(game.timeout_task)
    for task in game.disconnect_tasks.values():
        _cancel(task)

    delta_w: int | None = None
    delta_b: int | None = None
    decisive = result in (GameResult.WHITE, GameResult.BLACK, GameResult.DRAW)
    score = {GameResult.WHITE: 1.0, GameResult.BLACK: 0.0, GameResult.DRAW: 0.5}.get(result)

    async with get_session_factory()() as db:
        row = await db.get(Game, game.id)
        if row is not None:
            row.result = result
            row.end_reason = reason
            row.ended_at = now_utc()
            row.pgn = _pgn(game, result)

            if game.rated and decisive and score is not None:
                if game.mode == GameMode.ONLINE and game.black_id is not None:
                    delta_w, delta_b = await elo.apply_result(
                        db, RatingMode.ONLINE, game.white_id, game.black_id, score
                    )
                elif game.mode == GameMode.BOT and game.bot_level is not None:
                    anchor = BOT_ANCHOR_RATING[game.bot_level]
                    rating = await elo.get_or_create_rating(
                        db, game.white_id, RatingMode.BOT
                    )
                    delta_w = elo.delta(rating.value, anchor, score, rating.games)
                    rating.value += delta_w
                    rating.games += 1
                row.rating_delta_w = delta_w
                row.rating_delta_b = delta_b
            await db.commit()

            if delta_w is not None:
                mode_name = "ONLINE" if game.mode == GameMode.ONLINE else "BOT"
                white = await elo.get_or_create_rating(
                    db, game.white_id, RatingMode(mode_name)
                )
                await db.commit()
                await writer.record_rating(
                    user_id=game.white_id, mode=mode_name, value=white.value,
                    delta=delta_w, game_id=game.id,
                )
            if delta_b is not None and game.black_id is not None:
                black = await elo.get_or_create_rating(db, game.black_id, RatingMode.ONLINE)
                await db.commit()
                await writer.record_rating(
                    user_id=game.black_id, mode="ONLINE", value=black.value,
                    delta=delta_b, game_id=game.id,
                )

    _registry.pop(game.id, None)
    log.info("game_over", game_id=game.id, result=result.value, reason=reason)
    if game.on_over is not None:
        payload = {
            "game_id": game.id,
            "result": result.value,
            "reason": reason,
            "rating_delta": {"w": delta_w, "b": delta_b},
        }
        await game.on_over(game, payload)


def _pgn(game: LiveGame, result: GameResult) -> str:
    pgn_game = chess.pgn.Game.from_board(game.board)
    pgn_game.headers["Event"] = f"The Study — {game.mode.value.title()}"
    pgn_game.headers["Result"] = {
        GameResult.WHITE: "1-0",
        GameResult.BLACK: "0-1",
        GameResult.DRAW: "1/2-1/2",
        GameResult.ABORTED: "*",
    }[result]
    return str(pgn_game)
