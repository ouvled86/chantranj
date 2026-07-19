# PROGRESS — The Study

> Live tracker. Read this first every session. Update it every time a task lands.
> Detailed checkboxes live in [docs/TASKS.md](docs/TASKS.md).

## Status snapshot

| Phase | Name                                   | Status      | Progress |
|-------|----------------------------------------|-------------|----------|
| v1    | Static lesson app (design + content)   | ✅ Shipped  | 100%     |
| P     | Planning & documentation               | ✅ Shipped  | 100%     |
| 0     | Monorepo scaffold & tooling            | 🟨 Nearly done | 85%  |
| 1     | Backend foundation (auth, users, admin)| 🟨 Nearly done | 90%  |
| 2     | Database schema & content seeding      | 🟨 Nearly done | 85%  |
| 3     | Frontend foundation (React port)       | 🟨 Nearly done | 85%  |
| 4     | Online play (mode 1)                   | ⬜ Not started | 0%    |
| 5     | Engine service, bots & review (modes 2+3) | ⬜ Not started | 0% |
| 6     | Learning path & admin CMS              | ⬜ Not started | 0%    |
| 7     | Friends, presence & Puzzle Duel (mode 4) | ⬜ Not started | 0%  |
| 8     | Gamification (XP, achievements, boards)| ⬜ Not started | 0%    |
| 9     | Production hardening & deployment      | ⬜ Not started | 0%    |

**Overall: planning complete (stack revised 2026-07-18 → Python/FastAPI/TimescaleDB) — Phase 0 in progress.**

> ⚠ Machine note: dev machine has git + Node 26; **uv + Python 3.12 installed 2026-07-18**
> (backend tests now run locally on SQLite). Still **no Docker** — `make up`, TimescaleDB,
> Prometheus and the Alembic migration remain unverified until Docker Desktop is installed
> (TASKS 0.11).

## What exists right now

- v1 static app at repo root: `index.html`, `js/engine.js` (move application + pseudo-legal
  movegen), `js/content.js` (27 verified lessons/drills), `js/app.js` (lesson player, drill
  player, progress via localStorage), `css/style.css` (full design token system).
- Dev server config: `.claude/launch.json` → `npx http-server -p 4173 .`
- Planning suite: `CLAUDE.md`, this file, `docs/PLAN.md`, `docs/ARCHITECTURE.md`,
  `docs/TASKS.md`, `docs/CURRICULUM.md`.
- No git repo yet (git init is task 0.1). No backend, no containers yet.

## Next up

**→ Phase 4 (Mode 1: online play).** Start with 4.1/4.2 the server-authoritative game
service + server clocks (python-chess, asyncio), then 4.3 the `/ws/game` WebSocket endpoint
with Redis pub/sub, then matchmaking. Local dev note: backend runs on SQLite via
`DATABASE_URL=sqlite+aiosqlite:///./dev.db ENV=dev uv run uvicorn app.main:app --port 8000`
(seed first: `uv run python -m app.db.seed`); frontend `npm run dev` proxies /api+/ws to it.
**Redis is NOT installed locally** — matchmaking/pub-sub tests will need fakeredis or Docker.

Known dev-only quirk: Vite dev server occasionally logs React "invalid hook call" during
dependency re-optimization; the production build is console-clean (verified). Ignore in dev.

Still waiting on owner: 0.10 (GitHub repo name/visibility) · 0.11 (install Docker Desktop —
gates migrations 0002/0003, hypertables/caggs, Prometheus, and real-Redis testing) ·
2.7 (OK to download Lichess puzzle CSV).

## Session log

_Newest first. Keep entries to 2–4 lines._

### 2026-07-19 — Session 3c (learn API + Phase 3 frontend)
- Built /learn API (path/item/complete) with strict linear gating + tests (24 backend tests).
- Full React frontend: api client (CSRF + silent refresh), chess lib + Board port,
  lesson/drill players, gated path page, auth pages, shell/sidebar, settings; 9 fe tests.
- Verified LIVE end-to-end in browser (backend on local SQLite): login → complete lesson →
  solve 2 drills → progress 3/27, unlock chain works. Prod build console-clean.
- Left running for owner: backend :8000 (uvicorn bg), vite :5173, prod preview :4300.

### 2026-07-19 — Session 3b (Phase 2: schema, telemetry, seeds)
- Full domain models (games/ratings/friendships/curriculum/gamification) + telemetry Core
  tables; migrations 0002 (relational) and 0003 (hypertables, compression, retention,
  4 continuous aggregates — pg-only, verify at 0.11).
- v1 content auto-converted to seed JSON via Node; python-chess validator wired into
  seeding — it caught and fixed a REAL v1 content bug (opposition lesson `e6d7`→`d6d7`).
- Idempotent seeds: 12 stages, 27 items, 40 achievements, 6 dev users. 22 tests green,
  ruff+mypy clean. Cagg design notes: move_events has denormalized user_id; DAU via
  activity_daily (no COUNT DISTINCT in caggs).

### 2026-07-19 — Session 3 (Phase 1: auth/users/admin)
- Installed uv + Python 3.12 locally → backend verifiable without Docker (SQLite tests).
- Built Phase 1: JWT+rotating-refresh auth (family reuse detection), Google OAuth (manual
  flow, 503 till creds), RBAC, CSRF double-submit, redis rate limiting w/ memory fallback,
  security headers, request-id logging, Prometheus instrumentation, admin+audit, Alembic 0001.
- 19 tests green; ruff + mypy --strict clean. Deviations logged in TASKS: bcrypt over
  passlib, manual OAuth over Authlib. Gotcha for future tests: httpx jar files testserver
  cookies under domain "testserver.local".

### 2026-07-18 — Session 2b (Phase 0 execution)
- Git repo initialized on `main`; v1 committed + tagged `v1-static`; v1 moved to legacy-v1/.
- Scaffolded backend (FastAPI/uv/celery, tests written), engine (stockfish wrapper skeleton),
  frontend (Vite 8/React 19/TS 6/Tailwind 4 — build+test+lint green, theme tokens verified
  in browser), Dockerfiles (dev/prod targets), dev compose (8 services), Makefile, README.
- Remaining in Phase 0: 0.10 GitHub push (owner call) + 0.11 Docker verification (no Docker
  on this machine). Version note: vite pinned ^8 (plugin-react 6 requires it), vitest ^4.

### 2026-07-18 — Session 2 (stack pivot + Phase 0 start)
- **Stack corrected:** user's real current focus is their DevOps-internship homelab
  (automotive telemetry): Python 3.12 + FastAPI + **TimescaleDB** + Grafana. All docs
  (CLAUDE.md, PLAN, ARCHITECTURE, TASKS P0–P2 + stale refs) rewritten; Node/Express plan superseded.
- Context caveat learned: the "Internship" claude.ai Project is not readable from Claude Code;
  DB choice (TimescaleDB) confirmed via direct question. Saved to memory.
- Started Phase 0 execution (git init → scaffold).

### 2026-07-18 — Session 1 (planning)
- Built and verified v1: 27-item static lesson app ("The Study"), walnut/parchment design,
  all lessons + drills tested end-to-end in browser (27/27 completable, no JS errors).
- Inspected owner's ft_transcendence + Inception repos; locked the stack to mirror them
  (Express5/TS/Prisma/Postgres/Socket.IO + React19/Vite/Tailwind + Compose/NGINX/Prom/Grafana).
- Wrote full planning suite (PLAN, ARCHITECTURE, TASKS, CURRICULUM, CLAUDE.md, PROGRESS.md).
- Decisions of note: 4th game mode = Puzzle Duel; Elo v1 (not Glicko); engine as separate
  container; curriculum rebuilt as 12 gated stages seeded from v1's 27 items.
