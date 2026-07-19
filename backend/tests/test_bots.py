"""Bot Arena flow with a scripted fake engine — full plumbing minus Stockfish.

Real-engine integration (actual Stockfish moves) runs in the engine container
(engine/tests) once Docker is available.
"""

import pytest
from fastapi.testclient import TestClient

from app.chess import engine_client
from tests.test_ws_game import _move, _recv_until, _register, _ws


@pytest.fixture()
def scripted_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bot walks into the Scholar's mate."""
    replies = iter(["e7e5", "b8c6", "d7d6"])

    async def fake_botmove(fen: str, level: int) -> str:
        return next(replies)

    monkeypatch.setattr(engine_client, "botmove", fake_botmove)


def _auth(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


def test_bot_arena_scholars_mate_with_anchor_elo(
    client: TestClient, scripted_bot: None
) -> None:
    _, tok = _register(client)
    r = client.post(
        "/api/v1/games",
        json={"bot_level": 3, "time_control": {"base_min": None, "inc_sec": 0}, "rated": True},
        headers=_auth(tok),
    )
    assert r.status_code == 201, r.text
    game_id = r.json()["game_id"]

    with _ws(client, tok) as w:
        w.send_json({"type": "game:rejoin", "data": {"game_id": game_id}})
        state = _recv_until(w, "game:state")
        assert state["bot_level"] == 3
        assert state["black_id"] is None

        for mv in ("e2e4", "f1c4", "d1h5"):
            _move(w, game_id, mv)
            _recv_until(w, "game:move")  # my move
            reply = _recv_until(w, "game:move")  # bot reply
            assert reply["by"] == "b"

        _move(w, game_id, "h5f7")  # Qxf7#
        over = _recv_until(w, "game:over")
        assert over["result"] == "WHITE"
        assert over["reason"] == "checkmate"
        # Provisional (K=40) win vs the level-3 anchor (1000) from 1200: +10.
        assert over["rating_delta"]["w"] == 10
        assert over["rating_delta"]["b"] is None

    detail = client.get(f"/api/v1/games/{game_id}", headers=_auth(tok)).json()
    assert detail["mode"] == "BOT"
    assert "Qxf7#" in detail["pgn"]


def test_learn_mode_is_never_rated(client: TestClient, scripted_bot: None) -> None:
    _, tok = _register(client)
    r = client.post(
        "/api/v1/games",
        json={
            "bot_level": 2,
            "coach_level": 1,
            "time_control": {"base_min": None, "inc_sec": 0},
            "rated": True,  # ignored for LEARN
        },
        headers=_auth(tok),
    )
    assert r.status_code == 201
    game_id = r.json()["game_id"]

    with _ws(client, tok) as w:
        w.send_json({"type": "game:rejoin", "data": {"game_id": game_id}})
        state = _recv_until(w, "game:state")
        assert state["coach_level"] == 1
        w.send_json({"type": "game:resign", "data": {"game_id": game_id}})
        over = _recv_until(w, "game:over")
        assert over["rating_delta"]["w"] is None  # unrated

    detail = client.get(f"/api/v1/games/{game_id}", headers=_auth(tok)).json()
    assert detail["mode"] == "LEARN"
    assert detail["rated"] is False
