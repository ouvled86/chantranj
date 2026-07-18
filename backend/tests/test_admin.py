import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.user import AuditLog, Role, User
from tests.conftest import unique


def _promote_to_admin(client: TestClient, username: str) -> None:
    """Direct DB edit -- role changes normally require an existing admin."""

    async def _do() -> None:
        async with get_session_factory()() as db:
            user = await db.scalar(select(User).where(User.username == username))
            assert user is not None
            user.role = Role.ADMIN
            await db.commit()

    asyncio.run(_do())


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token") or ""}


def test_admin_routes_forbidden_for_users(client: TestClient, registered: dict[str, str]) -> None:
    r = client.get("/api/v1/admin/users")
    assert r.status_code == 403


def test_admin_list_and_patch_with_audit(client: TestClient, registered: dict[str, str]) -> None:
    _promote_to_admin(client, registered["username"])
    # Re-login to mint an access token carrying no stale state (role read from DB anyway).
    client.post(
        "/api/v1/auth/login",
        json={"identifier": registered["username"], "password": registered["password"]},
    )

    r = client.get("/api/v1/admin/users", params={"query": registered["username"]})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] >= 1

    # Create a victim and ban them.
    victim = f"victim_{unique()}"
    saved = {k: client.cookies.get(k) for k in ("access_token", "csrf_token")}
    client.post(
        "/api/v1/auth/register",
        json={"email": f"{victim}@t.dev", "username": victim, "password": "Passw0rd1"},
    )
    for k, v in saved.items():
        if v:
            client.cookies.set(k, v, domain="testserver.local", path="/")

    lookup = client.get("/api/v1/admin/users", params={"query": victim}).json()
    victim_id = lookup["items"][0]["id"]
    r = client.patch(
        f"/api/v1/admin/users/{victim_id}", json={"banned": True}, headers=_csrf(client)
    )
    assert r.status_code == 200, r.text

    async def _audit_rows() -> int:
        async with get_session_factory()() as db:
            rows = (
                await db.scalars(select(AuditLog).where(AuditLog.action == "admin.user_patch"))
            ).all()
            return len(rows)

    assert asyncio.run(_audit_rows()) >= 1

    # Banned user can no longer log in.
    r = client.post(
        "/api/v1/auth/login", json={"identifier": victim, "password": "Passw0rd1"}
    )
    assert r.status_code == 403
