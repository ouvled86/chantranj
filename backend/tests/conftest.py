"""Test config: SQLite in-memory DB (StaticPool), rate-limit reset per test.

Env vars are set BEFORE app imports so cached Settings pick them up.
"""

import asyncio
import os
import uuid

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-prod-0123456789abcdef"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"  # unreachable → memory fallback

import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401  (register models on Base.metadata)
from app.core.ratelimit import reset_memory_store
from app.db.base import Base
from app.db.session import get_engine
from app.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    reset_memory_store()


@pytest.fixture(autouse=True)
def _fresh_db() -> None:
    """One in-memory DB is shared process-wide (StaticPool), so wipe + recreate
    the schema before every test. Without this, rows a test inserts (e.g. an
    admin publishing an item) leak into later tests' counts."""

    async def _reset() -> None:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())


@pytest.fixture()
def client() -> TestClient:
    # Function-scoped: fresh cookie jar per test (schema create_all is idempotent).
    with TestClient(app) as c:  # context manager triggers lifespan → create_all
        yield c


# http.cookiejar files no-dot hostnames under "<host>.local" — match it exactly
# when planting cookies by hand.
COOKIE_DOMAIN = "testserver.local"


def unique() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def registered(client: TestClient) -> dict[str, str]:
    """A fresh registered+logged-in user; client carries their cookies afterwards."""
    u = unique()
    creds = {"email": f"u{u}@test.dev", "username": f"user_{u}", "password": "Passw0rd123"}
    r = client.post("/api/v1/auth/register", json=creds)
    assert r.status_code == 201, r.text
    return creds
