"""Engine service — a bounded pool of Stockfish processes behind HTTP.

Endpoints: /botmove (levels 1-8), /analyse (eval + best lines), /review
(full-game per-ply tags + lichess-style accuracy). DB-free by design; the
backend records engine_samples telemetry around its calls.
"""

import asyncio
import contextlib
import io
import math
import os
import random
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import chess
import chess.engine
import chess.pgn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

STOCKFISH_PATH = (
    os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish") or "/usr/games/stockfish"
)
POOL_SIZE = int(os.environ.get("ENGINE_POOL_SIZE", "2"))

# Bot strength axis (independent from coach level). Anchor ratings live in the
# backend; here only the stockfish shape of each level.
BOT_LEVELS: dict[int, dict[str, float]] = {
    1: {"skill": 0, "depth": 1, "blunder_p": 0.20},
    2: {"skill": 1, "depth": 2, "blunder_p": 0.12},
    3: {"skill": 3, "depth": 3, "blunder_p": 0.06},
    4: {"skill": 5, "depth": 4, "blunder_p": 0.0},
    5: {"skill": 8, "depth": 6, "blunder_p": 0.0},
    6: {"skill": 12, "depth": 8, "blunder_p": 0.0},
    7: {"skill": 16, "depth": 12, "blunder_p": 0.0},
    8: {"skill": 20, "time": 1.0, "blunder_p": 0.0},
}

_pool: asyncio.Queue[chess.engine.Protocol] = asyncio.Queue()
_engines: list[tuple[asyncio.SubprocessTransport, chess.engine.Protocol]] = []


def stockfish_available() -> bool:
    return shutil.which("stockfish") is not None or os.path.exists(STOCKFISH_PATH)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if stockfish_available():
        for _i in range(POOL_SIZE):
            transport, engine = await chess.engine.popen_uci(STOCKFISH_PATH)
            _engines.append((transport, engine))
            await _pool.put(engine)
    yield
    for _t, engine in _engines:
        with contextlib.suppress(Exception):
            await engine.quit()


app = FastAPI(title="The Study — Engine Service", version="0.2.0", lifespan=lifespan)


@asynccontextmanager
async def acquire() -> AsyncIterator[chess.engine.Protocol]:
    if not _engines:
        raise HTTPException(503, "Stockfish is not available in this environment")
    try:
        engine = await asyncio.wait_for(_pool.get(), timeout=20)
    except TimeoutError as exc:
        raise HTTPException(503, "Engine pool saturated") from exc
    try:
        yield engine
    finally:
        _pool.put_nowait(engine)


def _board_or_400(fen: str) -> chess.Board:
    try:
        return chess.Board(fen)
    except ValueError as exc:
        raise HTTPException(400, f"Bad FEN: {exc}") from exc


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {
        "status": "ok",
        "stockfish": stockfish_available(),
        "pool": len(_engines),
        "idle": _pool.qsize(),
    }


class BotMoveIn(BaseModel):
    fen: str
    level: int = Field(ge=1, le=8)


@app.post("/botmove")
async def botmove(body: BotMoveIn) -> dict[str, str]:
    board = _board_or_400(body.fen)
    if board.is_game_over():
        raise HTTPException(400, "Game is already over")
    cfg = BOT_LEVELS[body.level]
    # Low levels blunder like humans: sometimes just play something random.
    if random.random() < cfg["blunder_p"]:
        return {"move": random.choice(list(board.legal_moves)).uci()}
    async with acquire() as engine:
        await engine.configure({"Skill Level": int(cfg["skill"])})
        limit = chess.engine.Limit(
            depth=int(cfg["depth"]) if "depth" in cfg else None,
            time=cfg.get("time"),
        )
        result = await engine.play(board, limit)
    if result.move is None:
        raise HTTPException(500, "Engine returned no move")
    return {"move": result.move.uci()}


class AnalyseIn(BaseModel):
    fen: str
    depth: int = Field(default=12, ge=1, le=25)
    multipv: int = Field(default=1, ge=1, le=5)


@app.post("/analyse")
async def analyse(body: AnalyseIn) -> dict[str, list[dict[str, object]]]:
    board = _board_or_400(body.fen)
    if board.is_game_over():
        return {"lines": []}
    async with acquire() as engine:
        infos = await engine.analyse(
            board, chess.engine.Limit(depth=body.depth), multipv=body.multipv
        )
    lines: list[dict[str, object]] = []
    for info in infos if isinstance(infos, list) else [infos]:
        score = info["score"].white()
        pv = info.get("pv") or []
        lines.append(
            {
                "move": pv[0].uci() if pv else None,
                "eval_cp": score.score(),  # None when mate
                "mate": score.mate(),
                "pv": [m.uci() for m in pv[:6]],
            }
        )
    return {"lines": lines}


# ---------- full-game review ----------

def _win_pct(cp: int) -> float:
    """Lichess's win% model: 50 + 50*(2/(1+exp(-0.00368208*cp)) - 1)."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def _move_accuracy(win_before: float, win_after: float) -> float:
    drop = max(0.0, win_before - win_after)
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * drop) - 3.1669))


def _tag(win_before: float, win_after: float) -> str:
    drop = win_before - win_after
    if drop >= 20:
        return "blunder"
    if drop >= 10:
        return "mistake"
    if drop >= 5:
        return "inaccuracy"
    if drop <= 0.5:
        return "great"
    return "good"


class ReviewIn(BaseModel):
    pgn: str
    depth: int = Field(default=10, ge=6, le=18)


@app.post("/review")
async def review(body: ReviewIn) -> dict[str, object]:
    game = chess.pgn.read_game(io.StringIO(body.pgn))
    if game is None:
        raise HTTPException(400, "Unreadable PGN")
    moves = list(game.mainline_moves())
    board = game.board()

    # One eval per position (plies+1), single pass.
    evals: list[int] = []
    async with acquire() as engine:
        b = board.copy()
        for i in range(len(moves) + 1):
            if b.is_game_over():
                out = b.outcome()
                if out is not None and out.winner is not None:
                    evals.append(10_000 if out.winner == chess.WHITE else -10_000)
                else:
                    evals.append(0)
            else:
                info = await engine.analyse(b, chess.engine.Limit(depth=body.depth))
                score = info["score"].white()
                cp = score.score()
                if cp is None:  # forced mate somewhere in the line
                    mate = score.mate() or 0
                    cp = 10_000 if mate > 0 else -10_000
                evals.append(cp)
            if i < len(moves):
                b.push(moves[i])

    analysis: list[dict[str, object]] = []
    acc: dict[str, list[float]] = {"w": [], "b": []}
    replay = board.copy()
    for i, move in enumerate(moves):
        side = "w" if replay.turn == chess.WHITE else "b"
        san = replay.san(move)
        win_before = _win_pct(evals[i]) if side == "w" else 100 - _win_pct(evals[i])
        win_after = _win_pct(evals[i + 1]) if side == "w" else 100 - _win_pct(evals[i + 1])
        analysis.append(
            {
                "ply": i + 1,
                "side": side,
                "san": san,
                "uci": move.uci(),
                "eval_cp": evals[i + 1],
                "tag": _tag(win_before, win_after),
            }
        )
        acc[side].append(_move_accuracy(win_before, win_after))
        replay.push(move)

    return {
        "moves": analysis,
        "accuracy_w": round(sum(acc["w"]) / len(acc["w"]), 1) if acc["w"] else None,
        "accuracy_b": round(sum(acc["b"]) / len(acc["b"]), 1) if acc["b"] else None,
    }
