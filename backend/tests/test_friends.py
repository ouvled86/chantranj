"""Friend graph: request/accept, block precedence, search relations, leaderboard scope."""

from fastapi.testclient import TestClient

from tests.conftest import unique


def _reg(client: TestClient) -> tuple[str, str]:
    u = unique()
    creds = {"email": f"{u}@t.dev", "username": f"u_{u}", "password": "Passw0rd1"}
    assert client.post("/api/v1/auth/register", json=creds).status_code == 201
    token = client.cookies.get("access_token") or ""
    client.cookies.clear()  # Bearer-only auth → no cookie → CSRF-exempt
    return creds["username"], token


def _hdr(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


def test_request_accept_flow(client: TestClient) -> None:
    alice_name, alice = _reg(client)
    bob_name, bob = _reg(client)

    # Alice requests Bob.
    r = client.post("/api/v1/friends/requests", json={"username": bob_name}, headers=_hdr(alice))
    assert r.status_code == 201 and r.json()["status"] == "pending"

    # Bob sees an incoming request.
    view = client.get("/api/v1/friends", headers=_hdr(bob)).json()
    assert len(view["incoming"]) == 1
    fid = view["incoming"][0]["friendship_id"]
    assert view["incoming"][0]["username"] == alice_name

    # Bob accepts.
    acc = client.post(f"/api/v1/friends/requests/{fid}/accept", headers=_hdr(bob))
    assert acc.status_code == 200

    for tok in (alice, bob):
        view = client.get("/api/v1/friends", headers=_hdr(tok)).json()
        assert len(view["friends"]) == 1
        assert not view["incoming"] and not view["outgoing"]


def test_mutual_request_auto_accepts(client: TestClient) -> None:
    a_name, a = _reg(client)
    b_name, b = _reg(client)
    client.post("/api/v1/friends/requests", json={"username": b_name}, headers=_hdr(a))
    # B requests A back → should accept the existing one, not duplicate.
    r = client.post("/api/v1/friends/requests", json={"username": a_name}, headers=_hdr(b))
    assert r.json()["status"] == "accepted"
    assert len(client.get("/api/v1/friends", headers=_hdr(a)).json()["friends"]) == 1


def test_block_precedence(client: TestClient) -> None:
    a_name, a = _reg(client)
    b_name, b = _reg(client)
    # A blocks B (need B's user id — from search as A).
    search = client.get(f"/api/v1/friends/search?q={b_name}", headers=_hdr(a)).json()
    # search returns username/relation only; block by id via friends list requires id.
    # Fetch B's id through a fresh request cycle: register leaves us as B, so use /users/me.
    b_id = client.get("/api/v1/users/me", headers=_hdr(b)).json()["id"]
    assert client.post(f"/api/v1/friends/{b_id}/block", headers=_hdr(a)).status_code == 200

    # B can no longer send A a request.
    r = client.post("/api/v1/friends/requests", json={"username": a_name}, headers=_hdr(b))
    assert r.status_code == 403
    # A sees B as blocked in search.
    search = client.get(f"/api/v1/friends/search?q={b_name}", headers=_hdr(a)).json()
    assert search[0]["relation"] == "blocked"


def test_cannot_friend_self(client: TestClient) -> None:
    name, tok = _reg(client)
    r = client.post("/api/v1/friends/requests", json={"username": name}, headers=_hdr(tok))
    assert r.status_code == 400


def test_leaderboard_scope(client: TestClient) -> None:
    _, tok = _reg(client)
    # Empty but well-formed.
    r = client.get("/api/v1/leaderboards/duel", headers=_hdr(tok))
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert client.get("/api/v1/leaderboards/nonsense", headers=_hdr(tok)).status_code == 404
    r = client.get("/api/v1/leaderboards/online?scope=friends", headers=_hdr(tok))
    assert r.status_code == 200
