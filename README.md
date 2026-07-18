# ♞ The Study — Chess Training Platform

A production-grade chess training web app: a gated learning path with hand-verified lessons,
online play, coached bot games with 5 assistance levels, head-to-head puzzle duels, friends,
achievements — and a full observability stack, because the author cares about that part most.

> **Status:** in active development. Phase 0 (scaffold) — see [PROGRESS.md](PROGRESS.md).
> The finished v1 static lesson app lives in [`legacy-v1/`](legacy-v1/) and is fully usable.

## Why this stack

This project deliberately mirrors the stack of my DevOps internship homelab (automotive
telemetry): every chess game is treated as a **telemetry stream** — moves, clocks, engine
evals flow into **TimescaleDB hypertables** and surface in **Grafana** dashboards, the same
pipeline pattern as vehicle data.

| | |
|---|---|
| Backend | Python 3.12 · FastAPI (async) · SQLAlchemy 2.0 + Alembic · Pydantic v2 |
| Data | TimescaleDB (PostgreSQL 16 + time-series) · Redis 7 |
| Realtime | FastAPI WebSockets + Redis pub/sub |
| Chess | python-chess (server-authoritative) · Stockfish in a dedicated container |
| Jobs | Celery (post-game engine reviews) |
| Frontend | React 19 · Vite · TypeScript · Tailwind 4 |
| Infra | Docker Compose (dev/prod) · NGINX · Makefile · GitHub Actions |
| Observability | Prometheus · Grafana (infra metrics **and** game telemetry) |

## Quick start (dev)

Requires Docker (with Compose v2) and GNU Make.

```bash
make up        # full dev stack → http://localhost:8080
make logs      # tail everything
make test      # backend + engine + frontend suites
make down
```

Entry points: app via nginx `:8080` · API docs `:8000/docs` · Adminer `:8081` ·
Vite direct `:5173` · engine `:9000/healthz`.

## Repository layout

```
frontend/   React SPA          backend/   FastAPI API + Celery worker
engine/     Stockfish service  devops/    compose, Dockerfiles, monitoring
docs/       plan & contracts   legacy-v1/ the original static lesson app
```

Planning docs: [PLAN](docs/PLAN.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) ·
[TASKS](docs/TASKS.md) · [CURRICULUM](docs/CURRICULUM.md)

## License

TBD (Phase 9).
