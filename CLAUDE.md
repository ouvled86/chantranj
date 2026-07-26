# Shantranj — Chess Training Platform

Portfolio project: a production-grade chess training web app (lessons, bots with live coaching,
online play, friends, achievements). Owner is a 1337 (42 Network) student on a DevOps
internship — the stack deliberately mirrors the tech they are **currently mastering** in their
internship's automotive-telemetry homelab: **Python 3.12 + FastAPI** backend, **TimescaleDB**
(Postgres + time-series) primary store, **SQLAlchemy 2.0 async + Alembic + Pydantic v2**,
FastAPI WebSockets + Redis, **python-chess + Stockfish** for chess/engine, Celery for jobs,
**React 19 + Vite + Tailwind** frontend (unchanged from v1), Docker Compose + NGINX +
**Prometheus/Grafana** devops layer. Game telemetry (moves/clocks/evals, player metrics over
time) flows into TimescaleDB hypertables and Grafana — the direct mirror of the homelab.

NOTE: the earlier plan draft used an Express/Prisma/Socket.IO stack (mirroring the owner's
older ft_transcendence project). That was corrected on 2026-07-18 — see docs/PLAN.md decision
log. Ignore any lingering Node/Express references; Python/FastAPI/TimescaleDB is authoritative.

## Session protocol (IMPORTANT — quota can cut sessions short)

1. **Start of every session:** read `PROGRESS.md` first, then the relevant section of
   `docs/TASKS.md`. Resume from "Next up" in PROGRESS.md unless the user redirects.
2. **During work:** mark checkboxes in `docs/TASKS.md` (`[ ]` → `[x]`) the moment a task is
   done and verified — not in batches at the end. Update frequently; assume the session can
   die at any moment.
3. **After completing any task group or before any long operation:** update the
   "Session log" and "Next up" sections of `PROGRESS.md` (2–4 lines: what was done, what's
   in flight, exact next step).
4. Decisions already made live in `docs/PLAN.md` — do not re-litigate them; if a change is
   truly needed, record it in PLAN.md under "Decision log" with rationale.

## Doc map

- `PROGRESS.md` — live status: phase %, session log, next up. Update constantly.
- `docs/PLAN.md` — master plan, stack decisions + rationale, game modes spec, decision log.
- `docs/ARCHITECTURE.md` — services, containers, DB schema, API + socket contracts.
- `docs/TASKS.md` — full task breakdown, phases 0–9, checkboxes. The single source of truth
  for what is done.
- `docs/CURRICULUM.md` — learning-path redesign (12 stages), content authoring backlog,
  admin CMS model.

## Current repo state

The repo currently contains **v1**: a static vanilla-JS lesson app (index.html, js/, css/)
with 27 hand-verified lessons/drills. It runs via `npx http-server -p 4173 .`
(see `.claude/launch.json`). v1 is the design + content seed for the full app — the visual
design (walnut/parchment, tokens in css/style.css) and all content in js/content.js must be
preserved through the rebuild (content becomes DB seed data; design becomes the Tailwind theme).

## Conventions

- All chess legality/game state is **server-authoritative** via **python-chess**; the client
  (uses chess.js only for optimistic prediction) but the Python server decides.
- Every lesson/drill position and move line must be verified legal before seeding (v1 content
  already is; the seed script re-validates with python-chess).
- Windows dev machine, PowerShell; everything real runs **inside Docker** (Linux containers),
  so target Linux for the backend/engine. Prefer Make targets that work in Git Bash.
- Python tooling: **uv** for deps/venv, **Ruff** for lint+format, **mypy** for types,
  **pytest** (+ pytest-asyncio, httpx, testcontainers) for tests. FastAPI async everywhere.
