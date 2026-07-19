"""Real-Stockfish tests — run inside the engine container (skipped elsewhere)."""

import chess
import pytest
from fastapi.testclient import TestClient

from app.main import app, stockfish_available

pytestmark = pytest.mark.skipif(not stockfish_available(), reason="no stockfish binary")

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_botmove_is_legal_every_level() -> None:
    with TestClient(app) as c:
        for level in range(1, 9):
            r = c.post("/botmove", json={"fen": START, "level": level})
            assert r.status_code == 200, r.text
            move = chess.Move.from_uci(r.json()["move"])
            assert move in chess.Board(START).legal_moves


def test_analyse_returns_scored_line() -> None:
    with TestClient(app) as c:
        r = c.post("/analyse", json={"fen": START, "depth": 8})
        assert r.status_code == 200
        line = r.json()["lines"][0]
        assert line["move"] is not None
        assert line["eval_cp"] is not None or line["mate"] is not None


def test_review_tags_a_blunder() -> None:
    # 1. f3 e5 2. g4 Qh4# — white's 2.g4 must tag as a blunder.
    pgn = '[Result "0-1"]\n\n1. f3 e5 2. g4 Qh4# 0-1'
    with TestClient(app) as c:
        r = c.post("/review", json={"pgn": pgn, "depth": 8})
        assert r.status_code == 200
        body = r.json()
        tags = {m["ply"]: m["tag"] for m in body["moves"]}
        assert tags[3] == "blunder"  # 2. g4??
        assert body["accuracy_b"] > body["accuracy_w"]
