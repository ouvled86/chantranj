# PROGRESS — The Study

> Live tracker. Read this first every session. Update it every time a task lands.
> Detailed checkboxes live in [docs/TASKS.md](docs/TASKS.md).

## Status snapshot

| Phase | Name                                   | Status      | Progress |
|-------|----------------------------------------|-------------|----------|
| v1    | Static lesson app (design + content)   | ✅ Shipped  | 100%     |
| P     | Planning & documentation               | ✅ Shipped  | 100%     |
| 0     | Monorepo scaffold & tooling            | ✅ Done (0.10 deferred) | 95% |
| 1     | Backend foundation (auth, users, admin)| 🟨 Nearly done | 90%  |
| 2     | Database schema & content seeding      | 🟨 Nearly done | 85%  |
| 3     | Frontend foundation (React port)       | 🟨 Nearly done | 85%  |
| 4     | Online play (mode 1)                   | ✅ Playable | 90%  |
| 5     | Engine service, bots & review (modes 2+3) | ✅ Live | 95%  |
| 6     | Learning path & admin CMS              | ✅ Systems live | 80% |
| 7     | Friends, presence & Puzzle Duel (mode 4) | ✅ Live | 90%  |
| 8     | Gamification (XP, achievements, boards)| ✅ Live | 90%  |
| 9     | Production hardening & deployment      | ⬜ Not started | 0%    |

**Overall: phases 0–8 done and live-verified. Full product: 4 game modes, reviews, gated path
+ bosses, admin Content Studio, friends/presence/challenges, leaderboards, and gamification
(XP/levels/streaks/achievements + profile). Only Phase 9 (production hardening) remains.**

> Machine note: git + Node 26 + uv/Python 3.12 + **Docker Desktop (installed 2026-07-19,
> WSL2 backend)**. Full compose stack runs locally: `docker compose -f
> devops/compose/docker-compose.dev.yml up -d` → app at :8080, API :8000, engine :9000,
> adminer :8081. Pull tip: this connection needs SERIAL image pulls (retry loop), parallel
> pulls hit CDN TLS timeouts.

## What exists right now

- v1 static app at repo root: `index.html`, `js/engine.js` (move application + pseudo-legal
  movegen), `js/content.js` (27 verified lessons/drills), `js/app.js` (lesson player, drill
  player, progress via localStorage), `css/style.css` (full design token system).
- Dev server config: `.claude/launch.json` → `npx http-server -p 4173 .`
- Planning suite: `CLAUDE.md`, this file, `docs/PLAN.md`, `docs/ARCHITECTURE.md`,
  `docs/TASKS.md`, `docs/CURRICULUM.md`.
- No git repo yet (git init is task 0.1). No backend, no containers yet.

## Next up

**→ Phase 9 (production hardening & deployment):** GitHub Actions CI (ruff+mypy+pytest,
docker build), docker-compose.prod.yml (nginx TLS, WAF, resource limits, no dev mounts),
TLS/HSTS, Postgres backup cron + restore runbook, Grafana dashboards as code (the
homelab-mirror payoff: game telemetry from TimescaleDB + infra metrics from Prometheus),
Playwright e2e, load sanity, deploy + RUNBOOK. Also finally the GitHub push (task 0.10).

Deferred backlog: content authoring 6.8–6.10 (Content Studio ready); spectate 7.8; Lichess
puzzle CSV 2.7; profile accuracy-trend + opening-stats (8.6 slice); Redis leaderboard cache (8.5).

**Dev loop gotchas (important):** full stack via compose (:8080). Docker stops on PC sleep →
relaunch Docker Desktop, wait for engine, `docker compose ... up -d`. **`--reload` does NOT
work on Windows bind mounts — after changing backend code you MUST `docker compose restart
backend worker` (and it's uvicorn, not the reload watcher, that serves).** Also delete stale
`__pycache__` if imports look old. VITE_POLL=1 already set for the frontend watcher. Serial
image pulls (retry loop) — parallel hits CDN TLS timeouts. FastAPI here uses lazy router
inclusion, so introspecting `app.routes[].path` shows nothing — test routes over HTTP instead.

## Session log

_Newest first. Keep entries to 2–4 lines._

### 2026-07-21 — Session 8 (Phase 8: gamification LIVE)
- XP ledger (xp_events hypertable) + level curve + streaks (weekly freeze) + achievement
  engine evaluating condition_json from durable data; `on_event()` wired at item/boss/game/
  duel. Reward toasts (XP/level-up/unlock), sidebar level+streak chip, Profile page (level
  ring, ratings, rating sparkline, showcase), Achievements page. Stats + achievements REST.
- **Found+fixed a real bug live: achievement counters weren't user-scoped → another user's
  drill unlocked your badge. Added a two-user regression test.**
- Test-infra: switched to a file-based SQLite test DB (WAL + busy_timeout) — :memory:
  StaticPool couldn't survive the new cross-loop DB work in game-over. Per-test timeout 180s.
- 60 backend tests green, ruff+mypy clean, frontend build/lint/test green. Live-verified the
  whole reward loop in the browser.

### 2026-07-20 — Session 7 (Phase 7: friends + presence + Puzzle Duel LIVE)
- Friend graph (one-row-per-pair, block precedence, mutual auto-accept, search), `/ws/social`
  presence + friend challenges (accept → spawns a real online game via the /ws/game path),
  leaderboards (online/bot/duel, global/friends).
- Puzzle Duel (Mode 4): puzzle bank seeded from validated drills (12), duel engine (mean-rating
  selection, 180s clock, difficulty+combo scoring, wrong resets combo), `/ws/duel` matchmaking,
  duel Elo. Frontend: Friends page, Duel page (lobby+race+result), Leaderboard page, social store.
- **Live-verified: two /ws/duel clients matched through the running server, solver 170–0,
  duel Elo ±20; Friends page search/add works in the browser.** 54 backend tests green,
  ruff+mypy clean, frontend build/lint/test green.
- Debugging note recorded: `--reload` is inert on Windows bind mounts → must restart backend
  container to load new code (cost me a confusing "routes missing" detour; also lazy routing
  makes route introspection lie — curl the endpoints).

### 2026-07-20 — Session 6 (Phase 6: boss checkpoints + admin CMS LIVE)
- Boss system: `services/boss.py` verifies objectives from the finished Game row; game
  service generalized (bot plays either color, custom start_fen, side-aware Elo);
  `/learn/.../boss/start` + `/boss/verify`; 12 bosses seeded (mate/convert/draw-hold/beat-bot).
- Admin Content Studio: `admin_content.py` (stages/items CRUD, reorder, validate, publish
  gate) + React AdminPage (JSON editor + live board preview + validation display), admin-only nav.
- Test isolation fix: per-test drop/create in conftest (shared in-memory DB was leaking rows).
- **Live-verified through :8080:** admin injected an illegal move → validator blocked publish
  → fixed → published → item appeared in learner path; boss briefing → Begin → real K+Q vs K
  board. 45 backend tests green, ruff+mypy clean, frontend build/lint/test green.

### 2026-07-20 — Session 5b (Phase 5 complete: coach + review LIVE)
- Coach L1–L5 shipped: config-driven `services/coach.py`, coach:info after every ply,
  hints w/ budgets + arrow, server-side takebacks, L1 premove blunder-confirm; CoachPanel UI.
- Review pipeline: Celery `review.generate` (inline fallback w/o broker), Archive UI
  request→poll→accuracy+tags. **All verified vs REAL Stockfish through :8080** — coach
  winced at Ke2??, hint arrow drew, takeback rewound, review returned 96.8%/91.3%.
- War story logged (TASKS 5.9): illegal-FEN → stockfish segfault (exit −11) whose corpse
  poisoned the pool → added is_valid() 400-guard + self-healing respawn + lifespan reset.
- 37 backend + 6 real-engine container tests green; everything lint/type clean.

### 2026-07-19 — Session 5 (Docker + engine service + Bot Arena LIVE)
- Installed Docker Desktop (winget, WSL2). Full 8-service stack up; **task 0.11 cleared:
  Alembic 0001→0003 ran clean on real TimescaleDB — 6 hypertables, 4 caggs, 6 compression
  policies confirmed; seeds loaded; nginx :8080 serves the app.**
- Built the real engine service (UCI pool, /botmove /analyse /review w/ lichess-style
  accuracy), bot levels 1–8 + anchor Elo, bot driver in game service (engine called outside
  the lock), POST /games for BOT/LEARN, Bot Arena lobby UI. 33 backend tests green (bot flow
  tested via faked engine; real-engine game verified manually).
- **Played a live game vs real Stockfish through the containerized stack** (bot answered
  1.e4 with the Scandinavian); resignation → −30 BOT Elo; hypertable rows verified in psql.

### 2026-07-19 — Session 4b (Phase 4 frontend: online play is LIVE)
- Built the Play frontend: gameStore (WS client w/ auto-reconnect + sessionStorage rejoin),
  lobby (7 TC presets, rated toggle, queue), live game screen (clocks synced to server,
  move list, draw offer/respond, resign, result card w/ Elo delta), Archive page w/ PGN
  download. React-compiler lint gotchas: no Date.now() in render, no sync setState in effect.
- **Verified a real online game end-to-end:** browser (magnus_dev, white) vs scripted
  Python WS client (hikaru_dev) — matchmade at 5+0 rated, Scholar's mate, "You win! by
  checkmate", +20/−20 Elo both sides, Archive row + PGN correct.

### 2026-07-19 — Session 4 (Phase 4 backend: online play)
- Built the online-play backend: server-authoritative game service (python-chess, full
  result detection), monotonic clocks + flag watchdog, in-process matchmaking pools,
  /ws/game endpoint (queue/move/resign/draw/rejoin, cookie-JWT auth), Elo (K40/K20) with
  rating_history + move_events telemetry, games history REST w/ PGN.
- 31 backend tests green incl. 4 two-client WS scenarios. Two hard-won debugging lessons
  recorded in TASKS 4.2 (watchdog self-cancellation bug) and 4.10 (single-portal WS rig).
- pytest-timeout added (90s default) so hangs self-diagnose with thread dumps.

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
