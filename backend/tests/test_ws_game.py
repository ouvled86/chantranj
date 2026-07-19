"""Two-client WebSocket games: matchmaking, a scripted mate, flag fall, resignation.

IMPORTANT rig detail: all websocket sessions must share ONE event loop (like real
uvicorn), so both sockets are opened from the same entered TestClient and each
player's identity travels as an explicit access_token Cookie header.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from app.services import matchmaking


@pytest.fixture(autouse=True)
def _clean_queue() -> None:
    matchmaking.reset()


def _register(client: TestClient) -> tuple[str, str]:
    """Returns (username, access_token). Uses the shared client (single loop!),
    then clears its jar so identity travels only via explicit headers."""
    u = uuid.uuid4().hex[:8]
    r = client.post(
        "/api/v1/auth/register",
        json={"email": f"p{u}@t.dev", "username": f"p_{u}", "password": "Passw0rd1"},
    )
    assert r.status_code == 201
    token = client.cookies.get("access_token")
    assert token
    client.cookies.clear()
    return f"p_{u}", token


def _ws(client: TestClient, token: str) -> WebSocketTestSession:
    return client.websocket_connect("/ws/game", headers={"Cookie": f"access_token={token}"})


def _recv_until(ws: WebSocketTestSession, mtype: str, limit: int = 20) -> dict[str, Any]:
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["type"] == mtype:
            return msg["data"]
    raise AssertionError(f"never received {mtype}")


def _queue(ws: WebSocketTestSession, base_min: float | None = 5, rated: bool = True) -> None:
    ws.send_json(
        {
            "type": "queue:join",
            "data": {"time_control": {"base_min": base_min, "inc_sec": 0}, "rated": rated},
        }
    )


def _move(ws: WebSocketTestSession, game_id: int, uci: str) -> None:
    ws.send_json(
        {
            "type": "game:move",
            "data": {"game_id": game_id, "from": uci[:2], "to": uci[2:4], "promo": uci[4:]},
        }
    )


def test_matchmaking_and_fools_mate_with_elo(client: TestClient) -> None:
    white_name, white_tok = _register(client)
    black_name, black_tok = _register(client)

    with _ws(client, white_tok) as w, _ws(client, black_tok) as b:
        _queue(w)  # first in queue = white
        assert w.receive_json()["type"] == "queue:waiting"
        _queue(b)

        wm = _recv_until(w, "queue:matched")
        bm = _recv_until(b, "queue:matched")
        assert wm["color"] == "w" and bm["color"] == "b"
        assert wm["opponent"]["username"] == black_name
        assert bm["opponent"]["username"] == white_name
        game_id = wm["game_id"]

        # Fool's mate: 1.f3 e5 2.g4 Qh4#
        _move(w, game_id, "f2f3")
        assert _recv_until(w, "game:move")["san"] == "f3"
        _recv_until(b, "game:move")
        _move(b, game_id, "e7e5")
        _recv_until(w, "game:move")
        _recv_until(b, "game:move")
        _move(w, game_id, "g2g4")
        _recv_until(w, "game:move")
        _recv_until(b, "game:move")
        _move(b, game_id, "d8h4")

        over_w = _recv_until(w, "game:over")
        over_b = _recv_until(b, "game:over")
        assert over_w["result"] == "BLACK"
        assert over_w["reason"] == "checkmate"
        assert over_w["rating_delta"]["b"] > 0 > over_w["rating_delta"]["w"]
        assert over_b["result"] == "BLACK"

    # Durable record + PGN via REST (as white).
    client.cookies.set("access_token", white_tok, domain="testserver.local", path="/")
    games = client.get("/api/v1/games").json()
    assert games and games[0]["id"] == game_id
    detail = client.get(f"/api/v1/games/{game_id}").json()
    assert detail["result"] == "BLACK"
    assert "Qh4#" in detail["pgn"]


def test_illegal_and_out_of_turn_moves_rejected(client: TestClient) -> None:
    _, tok_w = _register(client)
    _, tok_b = _register(client)
    with _ws(client, tok_w) as w, _ws(client, tok_b) as b:
        _queue(w, rated=False)
        assert w.receive_json()["type"] == "queue:waiting"
        _queue(b, rated=False)
        game_id = _recv_until(w, "queue:matched")["game_id"]
        _recv_until(b, "queue:matched")

        _move(b, game_id, "e7e5")  # black tries to move first
        assert _recv_until(b, "error")["code"] == "not_your_turn"
        _move(w, game_id, "e2e5")  # illegal
        assert _recv_until(w, "error")["code"] == "illegal"
        _move(w, game_id, "e2e4")  # fine
        assert _recv_until(w, "game:move")["san"] == "e4"
        # End the game so no grace timers outlive the test.
        w.send_json({"type": "game:resign", "data": {"game_id": game_id}})
        _recv_until(b, "game:over")


def test_flag_fall_ends_game(client: TestClient) -> None:
    _, tok_w = _register(client)
    _, tok_b = _register(client)
    with _ws(client, tok_w) as w, _ws(client, tok_b) as b:
        _queue(w, base_min=0.01, rated=False)  # 600ms each
        assert w.receive_json()["type"] == "queue:waiting"
        _queue(b, base_min=0.01, rated=False)
        _recv_until(w, "queue:matched")
        _recv_until(b, "queue:matched")

        # White never moves; the watchdog should flag them.
        over = _recv_until(w, "game:over")
        assert over["result"] == "BLACK"
        assert over["reason"] == "timeout"


def test_resignation(client: TestClient) -> None:
    _, tok_w = _register(client)
    _, tok_b = _register(client)
    with _ws(client, tok_w) as w, _ws(client, tok_b) as b:
        _queue(w, rated=False)
        assert w.receive_json()["type"] == "queue:waiting"
        _queue(b, rated=False)
        game_id = _recv_until(w, "queue:matched")["game_id"]
        _recv_until(b, "queue:matched")

        w.send_json({"type": "game:resign", "data": {"game_id": game_id}})
        over = _recv_until(b, "game:over")
        assert over["result"] == "BLACK"
        assert over["reason"] == "resignation"
