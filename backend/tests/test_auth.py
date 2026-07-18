from fastapi.testclient import TestClient

from tests.conftest import unique


def test_register_sets_cookies_and_returns_user(client: TestClient) -> None:
    u = unique()
    r = client.post(
        "/api/v1/auth/register",
        json={"email": f"a{u}@t.dev", "username": f"alice_{u}", "password": "Passw0rd1"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == f"alice_{u}"
    assert "password" not in body
    cookies = r.headers.get_list("set-cookie")
    names = {c.split("=")[0] for c in cookies}
    assert {"access_token", "refresh_token", "csrf_token"} <= names
    # httpOnly on session cookies, not on csrf
    assert any("access_token" in c and "HttpOnly" in c for c in cookies)
    assert any("csrf_token" in c and "HttpOnly" not in c for c in cookies)


def test_register_duplicate_email_409(client: TestClient) -> None:
    u = unique()
    payload = {"email": f"dup{u}@t.dev", "username": f"dup_{u}", "password": "Passw0rd1"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    payload2 = dict(payload, username=f"other_{u}")
    r = client.post("/api/v1/auth/register", json=payload2)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "already_exists"


def test_register_weak_password_422(client: TestClient) -> None:
    u = unique()
    r = client.post(
        "/api/v1/auth/register",
        json={"email": f"w{u}@t.dev", "username": f"weak_{u}", "password": "onlyletters"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_login_wrong_password_401(client: TestClient, registered: dict[str, str]) -> None:
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": registered["email"], "password": "WrongPass1"},
    )
    assert r.status_code == 401


def test_login_and_me(client: TestClient, registered: dict[str, str]) -> None:
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": registered["username"], "password": registered["password"]},
    )
    assert r.status_code == 200
    me = client.get("/api/v1/users/me")
    assert me.status_code == 200
    assert me.json()["username"] == registered["username"]


def test_me_without_session_401(client: TestClient) -> None:
    client.cookies.clear()
    r = client.get("/api/v1/users/me")
    assert r.status_code == 401


def test_refresh_rotation_and_reuse_detection(
    client: TestClient, registered: dict[str, str]
) -> None:
    old_refresh = client.cookies.get("refresh_token")
    assert old_refresh

    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh

    # Replay the OLD token -> 401 and the whole family dies.
    client.cookies.set(
        "refresh_token", old_refresh, domain="testserver.local", path="/api/v1/auth"
    )
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "refresh_reused"

    # Even the newest token is now revoked.
    client.cookies.set(
        "refresh_token", new_refresh, domain="testserver.local", path="/api/v1/auth"
    )
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


def test_logout_revokes_and_clears(client: TestClient, registered: dict[str, str]) -> None:
    refresh = client.cookies.get("refresh_token")
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    client.cookies.set("refresh_token", refresh, domain="testserver.local", path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_login_rate_limited_429(client: TestClient) -> None:
    client.cookies.clear()
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "nobody@t.dev", "password": "Whatever1"},
        )
    r = client.post(
        "/api/v1/auth/login", json={"identifier": "nobody@t.dev", "password": "Whatever1"}
    )
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


def test_google_not_configured_503(client: TestClient) -> None:
    r = client.get("/api/v1/auth/google", follow_redirects=False)
    assert r.status_code == 503
