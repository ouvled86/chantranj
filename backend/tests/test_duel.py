"""Puzzle Duel: matchmaking pairs two players, scoring, and rating on finish."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.seed.run import seed_all
from app.services import duel as duel_service
from tests.test_ws_game import _recv_until, _register


@pytest.fixture(autouse=True)
def _seeded_and_clean(client: TestClient) -> None:
    asyncio.run(seed_all())
    duel_service.reset()
    from app.ws.duel import _reset_queue

    _reset_queue()


def _duel_ws(client: TestClient, tok: str):
    return client.websocket_connect("/ws/duel", headers={"Cookie": f"access_token={tok}"})


def test_matchmaking_pairs_players_and_sends_puzzles(client: TestClient) -> None:
    _, ta = _register(client)
    _, tb = _register(client)
    with _duel_ws(client, ta) as a, _duel_ws(client, tb) as b:
        a.send_json({"type": "duel:queue", "data": {}})
        assert a.receive_json()["type"] == "duel:waiting"
        b.send_json({"type": "duel:queue", "data": {}})

        start_a = _recv_until(a, "duel:start")
        start_b = _recv_until(b, "duel:start")
        assert start_a["total"] > 0
        assert start_a["fen"] and start_b["fen"]
        assert start_a["seconds_left"] > 0


def test_correct_solution_scores_and_wrong_resets_combo(client: TestClient) -> None:
    # Drive the duel service directly for deterministic puzzle content.
    async def scenario() -> dict[str, int]:
        await seed_all()
        duel = await duel_service.create_duel(1, 2, on_over=None)
        assert duel is not None
        # Give player 1 a known puzzle as their first: rebuild with a 1-move mate.
        from app.services.duel import Puzzle

        mate = Puzzle(
            fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
            line=[{"move": "d1d8", "san": "Rd8#"}],
            difficulty=800,
        )
        wrong_then = Puzzle(fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
                            line=[{"move": "d1d8", "san": "Rd8#"}], difficulty=800)
        duel.puzzles = [mate, wrong_then]
        import chess

        for uid in (1, 2):
            duel.progress[uid].board = chess.Board(mate.fen)
            duel.progress[uid].puzzle_idx = 0
            duel.progress[uid].cursor = 0

        solved = await duel_service.submit(duel, 1, "d1d8")
        wrong = await duel_service.submit(duel, 1, "a1a1")  # illegal-ish / wrong
        return {"solved_score": solved["score"], "combo_after_solve": solved["combo"],
                "combo_after_wrong": wrong["combo"], "result_solved": solved["result"],
                "result_wrong": wrong["result"]}

    out = asyncio.run(scenario())
    assert out["result_solved"] == "solved"
    assert out["solved_score"] > 0
    assert out["combo_after_solve"] == 1
    assert out["result_wrong"] == "wrong"
    assert out["combo_after_wrong"] == 0


def test_duel_finish_applies_rating() -> None:
    async def scenario() -> tuple[int, int]:
        await seed_all()
        from app.models import RatingMode
        from app.services import elo
        from app.services.duel import Puzzle

        captured: dict[str, object] = {}

        async def on_over(d, payload):  # type: ignore[no-untyped-def]
            captured.update(payload)

        duel = await duel_service.create_duel(1, 2, on_over=on_over)
        assert duel is not None
        duel.puzzles = [
            Puzzle(fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
                   line=[{"move": "d1d8", "san": "Rd8#"}], difficulty=800)
        ]
        import chess

        for uid in (1, 2):
            duel.progress[uid].board = chess.Board(duel.puzzles[0].fen)
        # Player 1 solves (done), player 2 fails (done) → both done → finish.
        await duel_service.submit(duel, 1, "d1d8")
        await duel_service.submit(duel, 2, "h1h1")
        # both done now; finish already triggered
        from app.db.session import get_session_factory

        async with get_session_factory()() as db:
            r1 = await elo.get_or_create_rating(db, 1, RatingMode.DUEL)
            r2 = await elo.get_or_create_rating(db, 2, RatingMode.DUEL)
            return r1.value, r2.value

    v1, v2 = asyncio.run(scenario())
    assert v1 > v2  # winner gained, loser lost


def test_duel_seeded_puzzle_bank_nonempty(client: TestClient) -> None:
    async def count() -> int:
        from sqlalchemy import func, select

        from app.db.session import get_session_factory
        from app.models import PuzzleBank

        async with get_session_factory()() as db:
            return await db.scalar(select(func.count()).select_from(PuzzleBank)) or 0

    assert asyncio.run(count()) >= 8
