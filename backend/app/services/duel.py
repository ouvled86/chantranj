"""Puzzle Duel — two players race the same puzzle gauntlet against a shared clock.

Server-authoritative: each player's board and cursor live here; the client only
sends attempted moves. Scoring = difficulty-scaled base + combo bonus; a wrong
move fails the current puzzle and resets the combo (puzzle-storm style).
"""

import asyncio
import contextlib
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import chess
import structlog
from sqlalchemy import select

from app.core.security import now_utc
from app.db.session import get_session_factory
from app.models import DuelMatch, PuzzleBank, RatingMode
from app.services import elo

log = structlog.get_logger()

DUEL_SECONDS = 180
GAUNTLET_SIZE = 8

_registry: dict[int, "LiveDuel"] = {}
OverCallback = Callable[["LiveDuel", dict[str, Any]], Awaitable[None]]


@dataclass
class Puzzle:
    fen: str
    line: list[dict[str, str]]
    difficulty: int


@dataclass
class PlayerProgress:
    board: chess.Board
    cursor: int = 0  # index into the current puzzle's line (even = solver to move)
    puzzle_idx: int = 0
    score: int = 0
    combo: int = 0
    solved: int = 0
    failed: int = 0
    done: bool = False


@dataclass
class LiveDuel:
    id: int
    a_id: int
    b_id: int
    puzzles: list[Puzzle]
    progress: dict[int, PlayerProgress] = field(default_factory=dict)
    status: str = "active"
    deadline: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    timer_task: asyncio.Task[None] | None = None
    on_over: OverCallback | None = None

    def opponent(self, uid: int) -> int:
        return self.b_id if uid == self.a_id else self.a_id

    def _puzzle_for(self, p: PlayerProgress) -> Puzzle | None:
        if p.puzzle_idx >= len(self.puzzles):
            return None
        return self.puzzles[p.puzzle_idx]

    def puzzle_payload(self, uid: int) -> dict[str, Any]:
        p = self.progress[uid]
        puzzle = self._puzzle_for(p)
        return {
            "puzzle_idx": p.puzzle_idx,
            "total": len(self.puzzles),
            "fen": p.board.fen() if puzzle else None,
            "score": p.score,
            "combo": p.combo,
            "done": p.done,
            "seconds_left": max(0, round(self.deadline - time.monotonic())),
        }

    def opponent_payload(self, uid: int) -> dict[str, Any]:
        opp = self.progress[self.opponent(uid)]
        return {"score": opp.score, "combo": opp.combo, "solved": opp.solved}


async def _select_puzzles(mean_rating: int) -> list[Puzzle]:
    async with get_session_factory()() as db:
        rows = (await db.scalars(select(PuzzleBank))).all()
    if not rows:
        return []
    ranked = sorted(rows, key=lambda r: abs(r.difficulty - mean_rating))
    chosen = ranked[: min(GAUNTLET_SIZE, len(ranked))]
    random.shuffle(chosen)  # same order sent to both players
    return [Puzzle(fen=r.fen, line=list(r.line), difficulty=r.difficulty) for r in chosen]


async def create_duel(
    a_id: int, b_id: int, on_over: OverCallback | None = None
) -> "LiveDuel | None":
    async with get_session_factory()() as db:
        ratings = {
            uid: (await elo.get_or_create_rating(db, uid, RatingMode.DUEL)).value
            for uid in (a_id, b_id)
        }
        await db.commit()
    mean = (ratings[a_id] + ratings[b_id]) // 2
    puzzles = await _select_puzzles(mean)
    if not puzzles:
        return None

    async with get_session_factory()() as db:
        row = DuelMatch(player_a_id=a_id, player_b_id=b_id, puzzle_ids=[])
        db.add(row)
        await db.commit()
        await db.refresh(row)

    duel = LiveDuel(id=row.id, a_id=a_id, b_id=b_id, puzzles=puzzles, on_over=on_over)
    for uid in (a_id, b_id):
        duel.progress[uid] = PlayerProgress(board=chess.Board(puzzles[0].fen))
    duel.deadline = time.monotonic() + DUEL_SECONDS
    duel.timer_task = asyncio.create_task(_timer(duel))
    _registry[duel.id] = duel
    log.info("duel_created", duel_id=duel.id, a=a_id, b=b_id, puzzles=len(puzzles))
    return duel


def get_live(duel_id: int) -> "LiveDuel | None":
    return _registry.get(duel_id)


def _points(difficulty: int, combo: int) -> int:
    return max(1, difficulty // 100) + combo * 2


def _advance_puzzle(duel: LiveDuel, p: PlayerProgress) -> None:
    p.puzzle_idx += 1
    p.cursor = 0
    nxt = duel._puzzle_for(p)  # noqa: SLF001 — same module
    if nxt is None:
        p.done = True
    else:
        p.board = chess.Board(nxt.fen)


async def submit(duel: LiveDuel, uid: int, uci: str) -> dict[str, Any]:
    """Apply one attempted solver move. Returns {result, ...progress}."""
    async with duel.lock:
        if duel.status != "active":
            return {"result": "over"}
        p = duel.progress[uid]
        if p.done:
            return {"result": "done", **duel.puzzle_payload(uid)}
        puzzle = duel._puzzle_for(p)  # noqa: SLF001
        if puzzle is None:
            p.done = True
            return {"result": "done", **duel.puzzle_payload(uid)}

        expected = puzzle.line[p.cursor]["move"]
        result: str
        if uci[:4] == expected[:4]:
            p.board.push(chess.Move.from_uci(expected))
            p.cursor += 1
            # auto-play opponent reply if present
            if p.cursor < len(puzzle.line):
                p.board.push(chess.Move.from_uci(puzzle.line[p.cursor]["move"]))
                p.cursor += 1
            if p.cursor >= len(puzzle.line):
                p.combo += 1
                p.score += _points(puzzle.difficulty, p.combo)
                p.solved += 1
                _advance_puzzle(duel, p)
                result = "solved"
            else:
                result = "progress"
        else:
            p.combo = 0
            p.failed += 1
            _advance_puzzle(duel, p)
            result = "wrong"

        payload = {"result": result, **duel.puzzle_payload(uid)}
        if p.done and duel.progress[duel.opponent(uid)].done:
            await _finish_locked(duel)
        return payload


async def _timer(duel: LiveDuel) -> None:
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.sleep(DUEL_SECONDS + 0.1)
        async with duel.lock:
            if duel.status == "active":
                await _finish_locked(duel)


async def _finish_locked(duel: LiveDuel) -> None:
    duel.status = "finished"
    task = duel.timer_task
    if task and not task.done() and task is not asyncio.current_task():
        task.cancel()

    a, b = duel.progress[duel.a_id], duel.progress[duel.b_id]
    if a.score > b.score:
        score_a = 1.0
    elif a.score < b.score:
        score_a = 0.0
    else:
        score_a = 0.5

    delta_a, delta_b = 0, 0
    async with get_session_factory()() as db:
        row = await db.get(DuelMatch, duel.id)
        if row is not None:
            row.score_a = a.score
            row.score_b = b.score
            row.ended_at = now_utc()
            delta_a, delta_b = await elo.apply_result(
                db, RatingMode.DUEL, duel.a_id, duel.b_id, score_a
            )
            await db.commit()

    _registry.pop(duel.id, None)
    log.info("duel_over", duel_id=duel.id, score_a=a.score, score_b=b.score)
    if duel.on_over is not None:
        await duel.on_over(
            duel,
            {
                "score_a": a.score,
                "score_b": b.score,
                "rating_delta": {duel.a_id: delta_a, duel.b_id: delta_b},
            },
        )


def reset() -> None:
    _registry.clear()
