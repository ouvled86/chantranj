"""Coach L1-L5 behavior with a scripted fake engine + review pipeline (inline path)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.chess import engine_client
from app.services.coach import build_info
from tests.test_ws_game import _move, _recv_until, _register, _ws


def _auth(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture()
def scripted_engine(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Bot plays a fixed defense; analyse evals are keyed BY POSITION so extra
    or reordered engine calls can never skew the script. The g4 position evals
    at -200 → a ~24 win% drop → blunder tag for the human."""
    import chess as pychess

    board = pychess.Board()
    fens: dict[str, int] = {board.fen(): 20}
    for uci, cp in (("e2e4", 30), ("e7e5", 30), ("g2g4", -200)):
        board.push_uci(uci)
        fens[board.fen()] = cp

    replies = iter(["e7e5", "b8c6", "d7d6"])

    async def fake_botmove(fen: str, level: int) -> str:
        return next(replies)

    async def fake_analyse(fen: str, depth: int = 12, multipv: int = 1) -> list[dict[str, Any]]:
        cp = fens.get(fen, -210)
        return [{"move": "g8f6", "eval_cp": cp, "mate": None, "pv": ["g8f6"]}]

    monkeypatch.setattr(engine_client, "botmove", fake_botmove)
    monkeypatch.setattr(engine_client, "analyse", fake_analyse)
    return {"fens": fens}


def test_build_info_level_matrix() -> None:
    # Same raw analysis, five disclosure levels.
    kwargs = {"ply": 4, "eval_cp": -180, "drop": 24.0, "hints_left": 3, "takebacks_left": 1}
    l1 = build_info(1, **kwargs)
    assert l1["tag"] == "blunder" and "note" in l1 and l1["eval_cp"] == -180
    l2 = build_info(2, **kwargs)
    assert l2["tag"] == "blunder" and "note" not in l2
    l3 = build_info(3, **kwargs)
    assert l3["tag"] == "blunder" and l3["eval_cp"] == -180
    l4 = build_info(4, **kwargs)
    assert l4["tag"] == "blunder" and "eval_cp" not in l4
    l5 = build_info(5, **kwargs)
    assert "tag" not in l5 and l5.get("critical") is True and "eval_cp" not in l5

    fine = build_info(4, ply=2, eval_cp=10, drop=1.0, hints_left=0, takebacks_left=0)
    assert "tag" not in fine  # whisper stays silent on good moves


def test_coach_flow_tags_hints_takeback(
    client: TestClient, scripted_engine: dict[str, Any]
) -> None:
    _, tok = _register(client)
    r = client.post(
        "/api/v1/games",
        json={
            "bot_level": 2,
            "coach_level": 2,  # Guided: 5 hints, 3 takebacks, tags
            "time_control": {"base_min": None, "inc_sec": 0},
        },
        headers=_auth(tok),
    )
    game_id = r.json()["game_id"]

    with _ws(client, tok) as w:
        w.send_json({"type": "game:rejoin", "data": {"game_id": game_id}})
        _recv_until(w, "game:state")

        # Move 1 (baseline coach:info messages interleave — drain by anchoring
        # on game:move echoes; each move's own coach:info follows its echo).
        _move(w, game_id, "e2e4")
        _recv_until(w, "game:move")  # e4 echo
        _recv_until(w, "game:move")  # bot reply e5

        # Move 2: eval crashes → tagged. The first coach:info AFTER the g4 echo
        # is g4's own (earlier infos were queued before the echo).
        _move(w, game_id, "g2g4")
        _recv_until(w, "game:move")  # g4 echo
        info = _recv_until(w, "coach:info")
        assert info["level"] == 2 and "eval_cp" in info
        assert info.get("tag") in ("mistake", "blunder")

        # Hint: budget decrements.
        w.send_json({"type": "coach:hint", "data": {"game_id": game_id}})
        hint = _recv_until(w, "coach:hint")
        assert hint["move"] == "g8f6"
        assert hint["hints_left"] == 4

        # Takeback: rewinds two plies.
        _recv_until(w, "game:move")  # bot reply to g4
        w.send_json({"type": "coach:takeback", "data": {"game_id": game_id}})
        state = _recv_until(w, "game:state")
        assert len(state["moves"]) == 2  # back to after 1.e4 e5
        assert state["takebacks_used"] == 1


def test_premove_verdict_blocks_blunders(
    client: TestClient, scripted_engine: dict[str, Any]
) -> None:
    _, tok = _register(client)
    r = client.post(
        "/api/v1/games",
        json={"bot_level": 1, "coach_level": 1, "time_control": {"base_min": None, "inc_sec": 0}},
        headers=_auth(tok),
    )
    game_id = r.json()["game_id"]
    with _ws(client, tok) as w:
        w.send_json({"type": "game:rejoin", "data": {"game_id": game_id}})
        _recv_until(w, "game:state")
        # evals iterator: 20 (before) then 30 (after) → fine move
        w.send_json(
            {"type": "coach:premove", "data": {"game_id": game_id, "from": "e2", "to": "e4"}}
        )
        v = _recv_until(w, "coach:premove_verdict")
        assert v["legal"] is True and v["ok"] is True
        # Illegal premove
        w.send_json(
            {"type": "coach:premove", "data": {"game_id": game_id, "from": "e2", "to": "e5"}}
        )
        v = _recv_until(w, "coach:premove_verdict")
        assert v["legal"] is False and v["ok"] is False


def test_review_inline_pipeline(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_review(pgn: str, depth: int = 10) -> dict[str, Any]:
        return {
            "moves": [{"ply": 1, "side": "w", "san": "f3", "uci": "f2f3", "tag": "inaccuracy"}],
            "accuracy_w": 41.5,
            "accuracy_b": 96.2,
        }

    async def fake_botmove(fen: str, level: int) -> str:
        raise AssertionError("not used")

    monkeypatch.setattr(engine_client, "review", fake_review)
    # Force the inline (no-broker) path.
    import app.api.v1.games as games_api

    monkeypatch.setattr(games_api, "_broker_reachable", lambda: False)

    # Fabricate a finished game via the ws quick path: resign a bot-less duel?
    # Simpler: create a LEARN game and resign it.
    monkeypatch.setattr(engine_client, "botmove", fake_botmove)
    _, tok = _register(client)
    r = client.post(
        "/api/v1/games",
        json={"bot_level": 1, "coach_level": 5, "time_control": {"base_min": None, "inc_sec": 0}},
        headers=_auth(tok),
    )
    game_id = r.json()["game_id"]
    with _ws(client, tok) as w:
        w.send_json({"type": "game:rejoin", "data": {"game_id": game_id}})
        _recv_until(w, "game:state")
        w.send_json({"type": "game:resign", "data": {"game_id": game_id}})
        _recv_until(w, "game:over")

    r = client.post(f"/api/v1/games/{game_id}/review", headers=_auth(tok))
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "ready"
    r = client.get(f"/api/v1/games/{game_id}/review", headers=_auth(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["accuracy_w"] == 41.5
    assert body["moves_analysis"][0]["tag"] == "inaccuracy"
