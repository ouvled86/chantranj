"""FastAPI application factory for The Study API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import CsrfMiddleware, RequestIdMiddleware, SecurityHeadersMiddleware
from app.db.session import get_engine

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.env)
    if settings.env == "test" or settings.database_url.startswith("sqlite"):
        # SQLite (tests / no-Docker local dev) skips Alembic; create schema in-loop.
        import app.models  # noqa: F401  (register models on Base.metadata)
        from app.db.base import Base

        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    log.info("startup", app=settings.app_name, env=settings.env)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Middleware executes in reverse add order: CORS → request-id → headers → CSRF → app.
    app.add_middleware(CsrfMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(api_router)

    from app.ws.game import router as ws_game_router

    app.include_router(ws_game_router)

    Instrumentator(excluded_handlers=["/metrics", "/healthz", "/readyz"]).instrument(app).expose(
        app, include_in_schema=False
    )

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["ops"])
    async def readyz() -> dict[str, object]:
        checks: dict[str, str] = {}
        status = "ok"
        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["db"] = "ok"
        except Exception:  # noqa: BLE001
            checks["db"] = "down"
            status = "degraded"
        checks["redis"] = "unchecked"  # wired in Phase 4 (matchmaking needs it hard)
        checks["engine"] = "unchecked"  # wired in Phase 5
        return {"status": status, "checks": checks}

    return app


app = create_app()
