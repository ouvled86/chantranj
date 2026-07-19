# TASKS — The Study

> The single source of truth for execution. Mark `[x]` the moment a task is done AND verified.
> Each phase has a **Definition of Done** — do not start the next phase until it holds
> (exception: content authoring in CURRICULUM.md can proceed in parallel any time).
> When a session ends mid-phase, update PROGRESS.md "Next up" with the exact next unchecked box.

Legend: `[ ]` todo · `[x]` done · `[~]` in progress / partially done (note why inline)

---

## Phase 0 — Monorepo scaffold & tooling

- [x] 0.1 `git init`; commit v1 as-is (tag `v1-static`); create `.gitignore` (python, __pycache__, .venv, node, dist, .env) — done, branch `main`
- [x] 0.2 Move static app → `legacy-v1/` (keep it runnable; update .claude/launch.json path) — done via `git mv`, history preserved
- [x] 0.3 Scaffold `frontend/` (Vite 8 + React 19 + TS 6 + Tailwind 4 + eslint + vitest 4) — verified: build ✓ tests ✓ lint ✓, placeholder renders with walnut/parchment tokens
- [x] 0.4 Scaffold `backend/` (uv project, FastAPI + uvicorn, pydantic-settings, structlog, celery; ruff + mypy strict + pytest configured; /healthz + /readyz + tests written) — runtime verify pending Docker (0.11)
- [x] 0.5 Scaffold `engine/` (FastAPI micro-service; /healthz reports stockfish availability; 501 stubs for Phase-5 endpoints; python-chess dep) — runtime verify pending Docker (0.11)
- [x] 0.6 `devops/containers/`: backend/engine/frontend Dockerfiles (uv, dev+prod targets, non-root prod, healthchecks; root build-context + .dockerignore) — build verify pending Docker (0.11)
- [x] 0.7 `devops/compose/docker-compose.dev.yml`: timescaledb (timescale/timescaledb:latest-pg16 — lighter than -ha, caggs included), redis, backend (reload), worker (celery), engine, frontend (vite), nginx dev proxy :8080, adminer; volumes + healthchecks — up verify pending Docker (0.11)
- [x] 0.8 Makefile: `up down logs ps migrate revision seed test lint fmt typecheck build prod-up prod-down` (+ `env` bootstrap); `.env.example` added
- [x] 0.9 Root README.md (portfolio-facing, telemetry-mapping story) + CONTRIBUTING.md (conventions)
- [ ] 0.10 GitHub repo created + pushed; branch protection on main — **needs owner: confirm repo name/visibility (gh auth)**
- [ ] 0.11 **BLOCKER:** install Docker Desktop (or run on a Docker-capable machine), then `make up` and verify: backend /healthz + /docs, engine /healthz (stockfish:true), worker connects to redis, nginx :8080 serves frontend, adminer reaches timescaledb; run `make test`

**DoD:** `make up` gives a running dev stack; `curl :8000/healthz` OK from the backend container; FastAPI `/docs` loads; frontend dev page loads through nginx; committed & pushed.

---

## Phase 1 — Backend foundation: auth, users, admin skeleton

- [x] 1.1 Config (pydantic-settings), structlog, global exception handlers (`{error:{code,message,details?}}`), request-id middleware
- [x] 1.2 DB layer: async SQLAlchemy engine/session (StaticPool for sqlite tests), `Base` w/ naming convention, Alembic init (async env); `User`+`RefreshToken`+`AuditLog` models; migration `0001` hand-written — exercised vs real TimescaleDB in 0.11
- [x] 1.3 Register/login — **deviation: `bcrypt` lib directly instead of stale passlib**; strong-password validator; JWT access 15m + rotating refresh 7d in httpOnly cookies (refresh path-scoped to /api/v1/auth)
- [x] 1.4 Refresh rotation with reuse detection (token families; replay revokes family) — covered by tests
- [x] 1.5 Google OAuth — **deviation: manual code flow (httpx + itsdangerous signed state) instead of Authlib** (fewer deps, no SessionMiddleware); 503 when unconfigured (tested); live flow needs real creds (owner: create Google OAuth client, fill .env)
- [x] 1.6 Auth dependency (cookie or Bearer) + `require_admin`; `/users/me` GET/PATCH (username/avatar/settings, 409 on taken username)
- [x] 1.7 Public profile `GET /users/{username}` (no email leak; 404 for banned/missing)
- [x] 1.8 Rate limiting: fixed-window, Redis-backed with in-process fallback; login/register 5/min/IP (429 tested); security-headers middleware; CORS locked
- [x] 1.9 CSRF double-submit middleware (cookie-auth unsafe methods; Bearer exempt; auth endpoints exempt) — tested both directions
- [x] 1.10 prometheus-fastapi-instrumentator wired, `/metrics` excluded from schema; network guarding happens at nginx (dev conf doesn't proxy /metrics) — visual check in 0.11
- [x] 1.11 Admin: `GET /admin/users` (search+pagination), `PATCH /admin/users/{id}` (role/ban) + audit rows; ban blocks login (tested)
- [x] 1.12 Tests: 19 passing (auth lifecycle, reuse detection, CSRF, rate limit, users, admin+audit) on local SQLite; ruff + mypy --strict clean. **Remaining for DoD: run against TimescaleDB via testcontainers/compose (0.11) + CI gate (Phase 9)**

**DoD:** full auth lifecycle demonstrable via `/docs` or curl ✓ (local); tests pass in CI (Phase 9); metrics visible in Prometheus (0.11).

---

## Phase 2 — Database schema, telemetry & content seeding

- [x] 2.1 SQLAlchemy models: Rating, Game, GameReview, Friendship, Stage, LearnItem, ItemProgress, PuzzleBank, Achievement, UserAchievement, Streak, DuelMatch + Alembic migration `0002` (hand-written)
- [x] 2.2 Telemetry hypertables (Core tables in models/telemetry.py + migration `0003`: create_hypertable, compression segmentby, clock_ticks 30d retention) — **runs only on postgres; verify at 0.11**. Note: move_events gained denormalized `user_id` (caggs can't join)
- [x] 2.3 Continuous aggregates in `0003`: leaderboard_daily (last()), player_accuracy_weekly (clean-move ratio), engine_latency_5m (avg/max; p95 via Prometheus), activity_daily (DAU derived — caggs can't COUNT DISTINCT) + refresh policies, autocommit_block — verify at 0.11
- [x] 2.4 Seed framework `app/db/seed/` (idempotent upserts by slug; `python -m app.db.seed`)
- [x] 2.5 v1 content ported via Node converter → `seed/data/curriculum_v1.json` (27 items, format verbatim); stage placement map per CURRICULUM.md in `seed/stage_map.py`
- [x] 2.6 python-chess validator (`seed/validate.py`) — seeding refuses illegal content. **Immediately caught+fixed a real v1 bug: opposition lesson step 6 was `e6d7`, king was on d6 → `d6d7`**
- [ ] 2.7 Puzzle bank starter: import ~200 tactics puzzles (Lichess puzzle DB CSV, CC0) — **needs owner OK to download the dataset** (or fetch on the Docker machine); schema+table ready
- [x] 2.8 40 achievement definitions seeded (declarative condition_json for the Phase 8 engine)
- [x] 2.9 Dev fixtures: 6 demo users incl. `admin` (password Passw0rd1, dev env only). Sample games + synthetic telemetry rows deferred to Phase 4/5 when the writers exist
- [~] 2.10 `make seed` wired; ERD export still todo (do on Docker machine or via dbdiagram from migration 0002)

**DoD:** fresh `make up && make migrate && make seed` → populated dev DB with hypertables + caggs (pending 0.11); validator passes 100% ✓ (local: 22 tests incl. seed idempotency 12 stages/27 items/40 achievements).

---

## Phase 3 — Frontend foundation (React port of v1)

- [x] 3.1 Design tokens ported to Tailwind 4 `@theme` (done in Phase 0; board CSS ported as `styles/board.css` this phase)
- [x] 3.2 App shell: react-router 7, sidebar layout (desktop + mobile drawer), auth-aware nav, protected routes — *error boundary + toasts deferred to Phase 4 polish*
- [x] 3.3 Auth pages (parchment cards): register, login, Google button (503 till creds), logout; silent refresh-retry in the API client keeps sessions alive
- [x] 3.4 `<Board/>` port: orientation flip, marks, SVG arrows, candidate dots, last-move, click input, auto-queen, shake — *drag input + underpromotion picker + keyboard a11y deferred (v1 parity is click-only)*
- [x] 3.5 Lesson + drill players (state machines ported from v1 app.js): steps/fen-jumps, movelist jumping, ← → keys, 2-stage hints, wrong-move feedback, auto-replies, takeaways
- [x] 3.6 Path page: 12 stages, DONE/AVAILABLE/LOCKED states from `/learn/path`, progress bar; gating enforced server-side (learn router built this phase, ahead of Phase 6 schedule)
- [ ] 3.7 Profile page v1 — deferred to Phase 8 (profile v2 was always there; account info lives in Settings meanwhile)
- [~] 3.8 Settings: account (username/avatar) ✓; board theme + sound toggle deferred
- [x] 3.9 Tests: chess lib (5: castling, promotion, movegen) + Board component (4: render, flip, clicks, marks) = 9 green — *drill-player interaction test still todo*

**DoD:** verified live in browser (dev+prod builds): login as seeded user → complete K+Q lesson → solve back-rank + fork drills → 3/27 persisted, next items unlock. Postgres persistence pending 0.11 (verified on SQLite). Prod build console-clean; dev-only Vite "invalid hook call" noise documented in PROGRESS.

---

## Phase 4 — Mode 1: Online play

- [ ] 4.1 Game service (server-authoritative): create/join, python-chess validation, move relay, result detection (mate/stale/50-move/3-fold/insufficient/timeout/resign/draw-agree); every accepted move writes a move_events telemetry row
- [ ] 4.2 Server clocks (monotonic, per-game interval mgmt); increment support; flag detection
- [ ] 4.3 WebSocket `/ws/game` endpoint: full contract per ARCHITECTURE §5 incl. rejoin with state resync; Redis pub/sub fan-out across workers
- [ ] 4.4 Matchmaking: redis queue, rating band widening over time, anti-self-match, cancel
- [ ] 4.5 Time control picker + custom FEN/Chess960 start options (FEN validated server-side; 960 castling = later stretch, disable castling rights for exotic FENs v1)
- [ ] 4.6 Elo service: K=40 provisional (<30 games) else 20; applied atomically with game end; rating history rows
- [ ] 4.7 Disconnect handling: 30s grace, abandon = loss (rated) / abort (<2 moves); reconnection banner UI
- [ ] 4.8 Game UI: board + clocks + move list + draw/resign + result modal + rematch offer
- [ ] 4.9 Game history page + PGN export/download; spectate-by-link (read-only socket join)
- [ ] 4.10 Socket integration test: scripted 2-client game incl. flag and reconnect scenarios
- [ ] 4.11 Load sanity: 50 concurrent bot-less games on dev machine without event-loop lag >100ms

**DoD:** two browsers play a full rated blitz game with correct clocks, result, and Elo updates; history shows the game with PGN.

---

## Phase 5 — Engine service, bots & review (modes 2 + 3)

- [ ] 5.1 Engine container: stockfish + UCI wrapper, worker pool, two priority lanes (interactive > batch), timeouts, /healthz, latency metrics
- [ ] 5.2 Bot levels 1–8 mapping (skill level, depth/time caps; weighted-random imperfection for 1–3); documented table
- [ ] 5.3 Mode 3 Bot Arena: create-game flow vs bot, separate Elo (bot ladder), rated toggle
- [ ] 5.4 Post-game review pipeline: queued `/review`, per-ply eval+best+tag (book/great/good/inaccuracy/mistake/blunder), accuracy %; review UI with eval graph + click-through board
- [ ] 5.5 Mode 2 Learn-by-Playing: coach engine channel (`coach:info`) computing live eval/threats/hints server-side
- [ ] 5.6 Coach levels L1–L5 implemented exactly per PLAN §3 table (config-driven, one code path)
- [ ] 5.7 Coach UI: eval bar, hint button w/ counters, blunder-confirm dialog (L1), move tags, takeback flow (rewinds server state)
- [ ] 5.8 "Critical moment" detector for L5 (eval swing threshold ≥1.5 pawns)
- [ ] 5.9 Engine failure degradation: bot games pause+retry, review jobs requeue; alert metric
- [ ] 5.10 Tests: bot move sanity per level, review tag thresholds, coach-level config matrix

**DoD:** play L1 coached game and see hints/warnings work; beat bot 1 in arena and see bot-Elo change; finished games get reviews with accuracy.

---

## Phase 6 — Learning path gating & admin CMS

- [ ] 6.1 Gating service: item unlock rules (previous item done) + stage unlock (boss done); admin bypass; API returns per-item status
- [ ] 6.2 Boss checkpoints: bossConfig (startFen, botLevel, playerColor, objective: win/draw/mate-in-N-moves/convert-endgame, move limit); server verifies outcome and marks progress
- [ ] 6.3 Boss UI: framed like a challenge (stage banner, objective text, retry)
- [ ] 6.4 Progress events → XP hooks (consumed in Phase 8)
- [ ] 6.5 Admin CMS — content list: stages/items table, drag reorder, draft/published badges, version bump on publish
- [ ] 6.6 Admin CMS — item editor: metadata form + JSON step/line editor with schema validation + live board preview (replays steps) + python-chess legality check on save; cannot publish invalid content
- [ ] 6.7 Admin CMS — stage editor + curriculum overview (item counts, completion funnel stats)
- [ ] 6.8 New-content authoring batch 1 (from CURRICULUM.md backlog): Stage 1–4 gaps (~15 items)
- [ ] 6.9 New-content authoring batch 2: Stage 5–8 gaps (~15 items)
- [ ] 6.10 New-content authoring batch 3: Stage 9–12 gaps (~12 items) — all validator-clean
- [ ] 6.11 Tests: gating edge cases (skip attempts return 403), boss verification, publish workflow

**DoD:** a fresh user must complete Stage 1 in order and beat its boss to see Stage 2; admin can author, preview, validate and publish a new drill end-to-end from the browser.

---

## Phase 7 — Social: friends, presence, challenges + Mode 4 Puzzle Duel

- [ ] 7.1 Friend API: request/accept/decline/remove/block (+ unique-pair constraint, block precedence)
- [ ] 7.2 WebSocket `/ws/social` endpoint: presence (online/in-game/idle), friend list live updates
- [ ] 7.3 Friends UI: search users, requests inbox, friend list with status dots + actions
- [ ] 7.4 Challenge flow: friend challenge with mode/time/position config → accept spawns game (modes 1/3)
- [ ] 7.5 Duel engine: puzzle set selection by mean rating, 3-min timer, scoring (difficulty × combo), server-side answer validation
- [ ] 7.6 WebSocket `/ws/duel` endpoint per ARCHITECTURE §5; matchmade + friend duels; duel Elo
- [ ] 7.7 Duel UI: split progress bars, combo flames, opponent progress ticker, results screen with per-puzzle breakdown
- [ ] 7.8 Spectate friend's ongoing game from friend list (read-only)
- [ ] 7.9 Abuse guards: challenge spam limits, block hides everywhere, report stub
- [ ] 7.10 Tests: friendship state machine, duel scoring, block precedence

**DoD:** two accounts befriend each other, see live presence, and finish a puzzle duel with correct scores and rating updates.

---

## Phase 8 — Gamification

- [ ] 8.1 XP ledger service + level curve; XP events wired: lesson/drill/boss complete, game win/draw, duel result, daily streak, achievement bonus
- [ ] 8.2 Streak service (daily activity, freeze token weekly); streak UI in header
- [ ] 8.3 Achievement engine: conditionJson evaluator on domain events; idempotent unlock; toast + confetti-free elegant unlock UI (fits the study aesthetic)
- [ ] 8.4 Seed the 40 achievements (appendix below) with icons
- [ ] 8.5 Leaderboards: global Elo (3 modes), weekly duel points, XP; friends-only filter; redis-cached
- [ ] 8.6 Profile v2: rating graphs (per mode), accuracy trend, opening stats (from PGN data), achievement showcase (pin 3)
- [ ] 8.7 Post-game & post-lesson XP summary screens ("+35 XP · streak 6 🔥")
- [ ] 8.8 Tests: xp math, level boundaries, achievement conditions, leaderboard cache invalidation

**Achievement appendix (categories):** Learning (First Steps, Stage 1–12 clears, Perfect Drill ×10, Bookworm=all lessons), Tactics (First Blood, Fork Master, Pin Cushion, Skewered, 10/25/50 duel wins, Combo ×8), Playing (First Win, Giant Slayer=beat bot 8, Flagged!=win on time, Comeback=win from −5 eval, Marathon=classical win, 100 games), Social (First Friend, Challenger ×10, Spectator), Dedication (7/30/100-day streak, Night Owl, Early Bird, Level 10/25/50).

**DoD:** playing and learning visibly feed XP/levels/streaks/achievements; leaderboards update; profile tells a player's story.

---

## Phase 9 — Production hardening & deployment

- [ ] 9.1 GitHub Actions CI: lint + typecheck + unit/integration on PR; docker build; push images to GHCR on main
- [ ] 9.2 docker-compose.prod.yml: nginx TLS termination, WAF (ModSecurity CRS) container, resource limits, restart policies, no dev mounts
- [ ] 9.3 TLS automation (certbot or acme.sh) + HSTS + security headers audit (Mozilla Observatory A)
- [ ] 9.4 Postgres backup cron (nightly pg_dump to volume, 7-day rotation) + tested restore runbook in docs/RUNBOOK.md
- [ ] 9.5 Grafana dashboards as code: API RED, sockets/games gauges, engine latency/queue, node/container resources; 4 alert rules
- [ ] 9.6 Playwright e2e in CI: register→lesson→bot game→friend→duel happy path
- [ ] 9.7 Load sanity (k6 or autocannon): 200 VU browse + 50 concurrent games; record numbers in docs
- [ ] 9.8 Secrets strategy documented; .env.example complete; no secret in git history (scan)
- [ ] 9.9 Deploy to VPS (or campus box): domain, prod compose up, smoke test; deployment guide in RUNBOOK.md
- [ ] 9.10 Portfolio polish: README with architecture diagram, GIFs, live demo link, "what I'd do next"; LICENSE
- [ ] 9.11 Stretch (optional): Vault for secrets, k8s manifests/helm chart, Chess960 castling, game chat

**DoD:** public URL, HTTPS, monitored, backed up, CI-gated. A recruiter can register and play within 60 seconds.
