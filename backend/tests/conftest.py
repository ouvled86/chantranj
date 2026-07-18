"""Test config: SQLite in-memory DB (StaticPool), rate-limit reset per test.

Env vars are set BEFORE app imports so cached Settings pick them up.
"""

import os
import uuid

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-prod-0123456789abcdef"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"  # unreachable → memory fallback

import pytest
from fastapi.testclient import TestClient

from app.core.ratelimit import reset_memory_store
from app.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    reset_memory_store()


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
