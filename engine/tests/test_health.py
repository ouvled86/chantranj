"""Engine service contract tests. Without a stockfish binary (e.g. Windows dev
host) the endpoints must degrade to clean 4xx/5xx, never crash. Real-engine
behavior is exercised in the container (see test_real_engine.py)."""

from fastapi.testclient import TestClient

from app.main import app, stockfish_available

client = TestClient(app)


def test_healthz_reports_pool() -> None:
    with TestClient(app) as c:
        r = c.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert isinstance(body["stockfish"], bool)
        assert body["pool"] >= 0


def test_botmove_rejects_bad_input() -> None:
    with TestClient(app) as c:
        assert c.post("/botmove", json={"fen": "not a fen", "level": 3}).status_code in (400, 503)
        empty = "8/8/8/8/8/8/8/8 w - - 0 1"
        assert c.post("/botmove", json={"fen": empty, "level": 9}).status_code == 422


def test_illegal_position_is_400_not_segfault() -> None:
    # Side not-to-move in check — this exact class of FEN once killed a pooled
    # stockfish (exit -11). It must be rejected before reaching the engine.
    bad = "r4rk1/ppq3pp/8/6N1/2Q5/8/P4PPP/6K1 w - - 0 1"
    with TestClient(app) as c:
        r = c.post("/analyse", json={"fen": bad})
        if stockfish_available():
            assert r.status_code == 400
            assert "Illegal position" in r.json()["detail"]
        else:
            assert r.status_code in (400, 503)
