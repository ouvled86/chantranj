from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz() -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stubs_are_501() -> None:
    for path in ("/botmove", "/analyse", "/review"):
        assert client.post(path).status_code == 501
