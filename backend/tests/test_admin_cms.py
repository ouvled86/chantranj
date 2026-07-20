"""Admin CMS: RBAC, draft→validate→publish gate, reorder, boss content check."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.seed.run import seed_all
from app.db.session import get_session_factory
from app.models import Role, User
from tests.conftest import unique


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token") or ""}


@pytest.fixture()
def admin(client: TestClient) -> dict[str, str]:
    asyncio.run(seed_all())
    u = unique()
    creds = {"email": f"a{u}@t.dev", "username": f"admin_{u}", "password": "Passw0rd1"}
    client.post("/api/v1/auth/register", json=creds)

    async def _promote() -> None:
        async with get_session_factory()() as db:
            user = await db.scalar(select(User).where(User.username == creds["username"]))
            assert user is not None
            user.role = Role.ADMIN
            await db.commit()

    asyncio.run(_promote())
    client.post(
        "/api/v1/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    return creds


def test_cms_requires_admin(client: TestClient, registered: dict[str, str]) -> None:
    assert client.get("/api/v1/admin/stages").status_code == 403
    assert client.get("/api/v1/admin/items").status_code == 403


def test_list_stages_with_counts(client: TestClient, admin: dict[str, str]) -> None:
    stages = client.get("/api/v1/admin/stages").json()
    assert len(stages) == 12
    board_vision = next(s for s in stages if s["slug"] == "board-vision")
    assert board_vision["item_count"] >= 3  # v1 items + boss


def test_publish_rejects_invalid_then_accepts_valid(
    client: TestClient, admin: dict[str, str]
) -> None:
    stages = client.get("/api/v1/admin/stages").json()
    stage_id = stages[0]["id"]
    slug = f"drill-{unique()}"

    # Create a draft with an ILLEGAL move line.
    r = client.post(
        "/api/v1/admin/items",
        json={
            "stage_id": stage_id,
            "slug": slug,
            "kind": "DRILL",
            "title": "Test drill",
            "order_idx": 50,
            "content_json": {
                "id": slug,
                "kind": "puzzle",
                "fen": "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
                "line": [{"move": "d1d8", "san": "Rd8#"}, {"move": "e2e5", "san": "??"}],
            },
        },
        headers=_csrf(client),
    )
    assert r.status_code == 201, r.text
    item_id = r.json()["id"]
    assert r.json()["published"] is False

    # Validate → invalid (second move e2e5 is illegal / no such piece).
    v = client.post(f"/api/v1/admin/items/{item_id}/validate", headers=_csrf(client)).json()
    assert v["valid"] is False and v["errors"]

    # Publish → refused.
    r = client.post(f"/api/v1/admin/items/{item_id}/publish", headers=_csrf(client))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_content"

    # Fix the content (single legal mate), then publish succeeds.
    client.patch(
        f"/api/v1/admin/items/{item_id}",
        json={
            "content_json": {
                "id": slug,
                "kind": "puzzle",
                "fen": "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
                "line": [{"move": "d1d8", "san": "Rd8#"}],
            }
        },
        headers=_csrf(client),
    )
    v = client.post(f"/api/v1/admin/items/{item_id}/validate", headers=_csrf(client)).json()
    assert v["valid"] is True
    r = client.post(f"/api/v1/admin/items/{item_id}/publish", headers=_csrf(client))
    assert r.status_code == 200
    assert r.json()["published"] is True and r.json()["version"] == 2


def test_reorder_items(client: TestClient, admin: dict[str, str]) -> None:
    stages = client.get("/api/v1/admin/stages").json()
    stage = next(s for s in stages if s["slug"] == "tactics-1")
    items = client.get(f"/api/v1/admin/items?stage_id={stage['id']}").json()
    slugs = [i["slug"] for i in items]
    reversed_slugs = list(reversed(slugs))
    r = client.post(
        "/api/v1/admin/items/reorder",
        json={"stage_id": stage["id"], "ordered_slugs": reversed_slugs},
        headers=_csrf(client),
    )
    assert r.status_code == 200
    after = client.get(f"/api/v1/admin/items?stage_id={stage['id']}").json()
    assert [i["slug"] for i in after] == reversed_slugs
