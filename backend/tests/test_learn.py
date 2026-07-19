"""Linear gating: one AVAILABLE item, everything after LOCKED, DONE stays open."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.seed.run import seed_all


@pytest.fixture(autouse=True)
def _seeded(client: TestClient) -> None:
    asyncio.run(seed_all())  # idempotent


def _path(client: TestClient) -> list[dict]:
    r = client.get("/api/v1/learn/path")
    assert r.status_code == 200, r.text
    return r.json()


def _flat(path: list[dict]) -> list[dict]:
    return [item for stage in path for item in stage["items"]]


def test_path_shape_and_initial_gating(client: TestClient, registered: dict[str, str]) -> None:
    path = _path(client)
    assert len(path) == 12
    items = _flat(path)
    assert len(items) == 27
    assert items[0]["slug"] == "kq-mate"  # stage 1, first seeded item
    assert items[0]["status"] == "AVAILABLE"
    assert all(i["status"] == "LOCKED" for i in items[1:])


def test_complete_unlocks_next_and_locked_is_403(
    client: TestClient, registered: dict[str, str]
) -> None:
    csrf = {"X-CSRF-Token": client.cookies.get("csrf_token") or ""}

    # Locked item: neither readable nor completable.
    assert client.get("/api/v1/learn/items/lucena").status_code == 403
    r = client.post("/api/v1/learn/items/lucena/complete", headers=csrf)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "locked"

    # The available item is readable and completable.
    r = client.get("/api/v1/learn/items/kq-mate")
    assert r.status_code == 200
    assert r.json()["content"]["id"] == "kq-mate"
    assert client.post("/api/v1/learn/items/kq-mate/complete", headers=csrf).status_code == 200

    items = _flat(_path(client))
    assert items[0]["status"] == "DONE"
    assert items[1]["slug"] == "backrank"
    assert items[1]["status"] == "AVAILABLE"
    assert items[2]["status"] == "LOCKED"

    # Completing twice is idempotent.
    assert client.post("/api/v1/learn/items/kq-mate/complete", headers=csrf).status_code == 200
