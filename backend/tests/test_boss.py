"""Boss checkpoints: gating, start (either color), objective verification."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.chess import engine_client
from app.db.seed.run import seed_all
from app.db.session import get_session_factory
from app.models import Game, GameResult
from app.services import boss as boss_service


def _auth(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _seeded(client: TestClient) -> None:
    asyncio.run(seed_all())


def test_verify_is_pure_objective_check() -> None:
    # win objective
    g = Game(white_id=1, black_id=None, result=GameResult.WHITE, end_reason="checkmate", pgn="")
    cfg = {"player_color": "white", "objective": "win"}
    assert boss_service.verify(g, cfg, 1)[0] is True
    g.result = GameResult.BLACK
    assert boss_service.verify(g, cfg, 1)[0] is False

    # draw objective (hold as black): draw passes, loss fails
    gd = Game(white_id=None, black_id=2, result=GameResult.DRAW, pgn="")
    cfgd = {"player_color": "black", "objective": "draw"}
    assert boss_service.verify(gd, cfgd, 2)[0] is True
    gd.result = GameResult.WHITE  # white (bot) won → black lost the hold
    assert boss_service.verify(gd, cfgd, 2)[0] is False

    # checkmate-specific: a win by resignation must fail
    gr = Game(white_id=1, black_id=None, result=GameResult.WHITE, end_reason="resignation", pgn="")
    cfg_mate = {"player_color": "white", "objective": "checkmate"}
    assert boss_service.verify(gr, cfg_mate, 1)[0] is False


def test_boss_is_locked_until_reached(client: TestClient, registered: dict[str, str]) -> None:
    # Deep boss is locked for a brand-new user.
    r = client.get("/api/v1/learn/items/capstone-final-boss")
    assert r.status_code == 403


def test_boss_cannot_be_completed_without_winning(
    client: TestClient, registered: dict[str, str]
) -> None:
    # Make the user an admin-free path: use admin bypass to read the boss, but
    # completion must still refuse the /complete shortcut.
    r = client.post(
        "/api/v1/learn/items/boss-board-vision/complete",
        headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""},
    )
    # Either locked (normal user) or boss_requires_win (if reachable) — never 200.
    assert r.status_code in (403, 409)


def test_boss_start_and_verify_win(
    client: TestClient, registered: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Promote to admin to bypass gating and reach any boss directly.
    from sqlalchemy import select

    from app.models import Role, User

    async def _promote() -> None:
        async with get_session_factory()() as db:
            u = await db.scalar(select(User).where(User.username == registered["username"]))
            assert u is not None
            u.role = Role.ADMIN
            await db.commit()

    asyncio.run(_promote())
    client.post(
        "/api/v1/auth/login",
        json={"identifier": registered["username"], "password": registered["password"]},
    )

    # Bot (black, lone king) will just shuffle; we don't actually mate here —
    # instead we verify the objective logic against a fabricated finished game.
    async def fake_botmove(fen: str, level: int) -> str:
        import chess

        board = chess.Board(fen)
        return next(iter(board.legal_moves)).uci()

    monkeypatch.setattr(engine_client, "botmove", fake_botmove)

    csrf = {"X-CSRF-Token": client.cookies.get("csrf_token") or ""}
    r = client.post("/api/v1/learn/items/boss-board-vision/boss/start", headers=csrf)
    assert r.status_code == 201, r.text
    game_id = r.json()["game_id"]

    # Force the game to a won-by-checkmate state (simulating a completed fight).
    async def _finish() -> None:
        async with get_session_factory()() as db:
            g = await db.get(Game, game_id)
            assert g is not None
            g.result = GameResult.WHITE
            g.end_reason = "checkmate"
            g.pgn = '[Result "1-0"]\n\n1. Qe7# 1-0'
            await db.commit()

    asyncio.run(_finish())

    r = client.post(
        "/api/v1/learn/items/boss-board-vision/boss/verify",
        json={"game_id": game_id},
        headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""},
    )
    assert r.status_code == 200, r.text
    assert r.json()["passed"] is True

    # Now the boss shows DONE on the path.
    path = client.get("/api/v1/learn/path").json()
    boss = next(
        i for s in path for i in s["items"] if i["slug"] == "boss-board-vision"
    )
    assert boss["status"] == "DONE"
