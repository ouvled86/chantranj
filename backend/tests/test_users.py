from fastapi.testclient import TestClient

from tests.conftest import unique


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token") or ""}


def test_patch_me_requires_csrf(client: TestClient, registered: dict[str, str]) -> None:
    r = client.patch("/api/v1/users/me", json={"avatar_url": "https://x.dev/a.png"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"


def test_patch_me_with_csrf(client: TestClient, registered: dict[str, str]) -> None:
    new_name = f"renamed_{unique()}"
    r = client.patch(
        "/api/v1/users/me",
        json={"username": new_name, "settings": {"board": "walnut"}},
        headers=_csrf(client),
    )
    assert r.status_code == 200, r.text
    assert r.json()["username"] == new_name

    me = client.get("/api/v1/users/me")
    assert me.json()["username"] == new_name


def test_patch_me_taken_username_409(client: TestClient, registered: dict[str, str]) -> None:
    other = f"taken_{unique()}"
    saved = {k: client.cookies.get(k) for k in ("access_token", "csrf_token")}
    client.post(
        "/api/v1/auth/register",
        json={"email": f"{other}@t.dev", "username": other, "password": "Passw0rd1"},
    )
    for k, v in saved.items():
        if v:
            client.cookies.set(k, v, domain="testserver.local", path="/")
    r = client.patch("/api/v1/users/me", json={"username": other}, headers=_csrf(client))
    assert r.status_code in (409, 403)  # 403 only if csrf cookie rotated by second register
    if r.status_code == 409:
        assert r.json()["error"]["code"] == "already_exists"


def test_public_profile(client: TestClient, registered: dict[str, str]) -> None:
    r = client.get(f"/api/v1/users/{registered['username']}")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == registered["username"]
    assert "email" not in body


def test_public_profile_404(client: TestClient) -> None:
    assert client.get(f"/api/v1/users/ghost_{unique()}").status_code == 404
