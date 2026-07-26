# TASKS — Shantranj

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
- [x] 0.10 GitHub repo created + pushed — done 2026-07-22: private repo `chantranj` (github.com/ouvled86/chantranj), `main` tracking `origin/main`, all 11 commits pushed after owner ran `gh auth login`
- [x] 0.11 Docker Desktop installed (winget, WSL2 backend) 2026-07-19. Full stack verified: 8 services up (backend/worker/engine/timescaledb/redis/nginx/frontend/adminer); backend+engine healthz ✓ (stockfish:true, pool 2); **Alembic 0001→0003 clean on real TimescaleDB: 6 hypertables, 4 continuous aggregates, 6 compression policies confirmed via psql**; seeds into TimescaleDB ✓; nginx :8080 serves the app ✓. Gotcha: serial `docker pull` with retries beats parallel pulls on this connection (CDN TLS timeouts)

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
- [~] 2.7 Puzzle bank: 12 puzzles seeded from the validated v1 drills (Phase 7, `seed/puzzles.py`) — enough to run duels. Bulk ~200-puzzle Lichess CSV import still optional (needs owner OK to download); schema unchanged, extends cleanly
- [x] 2.8 40 achievement definitions seeded (declarative condition_json for the Phase 8 engine)
- [x] 2.9 Dev fixtures: 6 demo users incl. `admin` (password Passw0rd1, dev env only). Sample games + synthetic telemetry rows deferred to Phase 4/5 when the writers exist
- [~] 2.10 `make seed` wired; ERD export still todo (do on Docker machine or via dbdiagram from migration 0002)

**DoD:** fresh `make up && make migrate && make seed` → populated dev DB with hypertables + caggs (pending 0.11); validator passes 100% ✓ (local: 22 tests incl. seed idempotency 12 stages/27 items/40 achievements).

---

## Phase 3 — Frontend foundation (React port of v1)

- [x] 3.1 Design tokens ported to Tailwind 4 `@theme` (done in Phase 0; board CSS ported as `styles/board.css` this phase). **2026-07-26 redesign:** tokens extended (elevation `--shadow-e1/e2/e3`, brass/glow, radius, walnut/parchment ramp) + shared component classes; app renamed **Shantranj**; new `components/icons.tsx` inline-SVG set. Merged from the Claude Design handoff — see `docs/REDESIGN_HANDOFF.md`
- [~] 3.10 Redesign rollout: Layout, AuthPages, PathPage, PlayPage, CoachPanel, Clock, board + foundations done and verified. Remaining screens (Profile, Achievements, Duel, Boss, Friends, Leaderboard, Archive, lesson/drill players, Admin, Settings, rewardToast) still on the old flat styling — recipes in `docs/REDESIGN_HANDOFF.md`
- [x] 3.2 App shell: react-router 7, sidebar layout (desktop + mobile drawer), auth-aware nav, protected routes — *error boundary + toasts deferred to Phase 4 polish*
- [x] 3.3 Auth pages (parchment cards): register, login, Google button (503 till creds), logout; silent refresh-retry in the API client keeps sessions alive
- [x] 3.4 `<Board/>` port: orientation flip, marks, SVG arrows, candidate dots, last-move, click input, auto-queen, shake — *drag input + underpromotion picker + keyboard a11y deferred (v1 parity is click-only)*
- [x] 3.5 Lesson + drill players (state machines ported from v1 app.js): steps/fen-jumps, movelist jumping, ← → keys, 2-stage hints, wrong-move feedback, auto-replies, takeaways
- [x] 3.6 Path page: 12 stages, DONE/AVAILABLE/LOCKED states from `/learn/path`, progress bar; gating enforced server-side (learn router built this phase, ahead of Phase 6 schedule)
- [x] 3.7 Profile page — delivered in Phase 8 (level ring, ratings, rating sparkline, streak, achievement showcase); account info in Settings
- [~] 3.8 Settings: account (username/avatar) ✓; board theme + sound toggle deferred
- [x] 3.9 Tests: chess lib (5: castling, promotion, movegen) + Board component (4: render, flip, clicks, marks) = 9 green — *drill-player interaction test still todo*

**DoD:** verified live in browser (dev+prod builds): login as seeded user → complete K+Q lesson → solve back-rank + fork drills → 3/27 persisted, next items unlock. Postgres persistence pending 0.11 (verified on SQLite). Prod build console-clean; dev-only Vite "invalid hook call" noise documented in PROGRESS.

---

## Phase 4 — Mode 1: Online play

- [x] 4.1 Game service (server-authoritative, `services/games.py`): python-chess validation, result detection via `board.outcome(claim_draw=True)` (mate/stale/insufficient/75-move/5-fold + 50-move/3-fold auto-claim), resign, draw offer/accept; every accepted move → move_events telemetry
- [x] 4.2 Server clocks: monotonic, increment support, per-game async watchdog for flag falls. **War story: watchdog self-cancelled inside `_finish_locked` (it cancels timeout_task = itself), CancelledError swallowed by its own suppress → flag games half-finished. Fix: `_cancel` never cancels `current_task`.**
- [x] 4.3 WebSocket `/ws/game`: queue join/leave, move/resign/draw, rejoin+resync, opponent-connection events, cookie-JWT handshake auth (4401 close). **In-process fan-out (single-worker correct); Redis pub/sub variant = 0.11/Phase 9 when Docker exists**
- [~] 4.4 Matchmaking: in-process FIFO pools per (TC, rated), anti-self-match, leave-on-disconnect. **Redis pool + rating-band widening pending Docker**
- [~] 4.5 Time control picker UI ✓ (7 presets incl. untimed, rated toggle); custom FEN/960 start deferred to friend challenges (Phase 7)
- [x] 4.6 Elo service: K=40 provisional/K=20, applied atomically at game end, deltas on game row + rating_history telemetry; unit-tested
- [x] 4.7 Disconnect handling: 30s grace task → abandonment loss (abort if <2 moves); reconnect cancels grace; "disconnected — 30s to forfeit" banner in game UI; socket auto-reconnects + rejoins via sessionStorage game id
- [x] 4.8 Game UI (`features/play/`): lobby (TC picker, rated toggle, queue), live screen (Board, ticking cosmetic clocks synced to server, move list, draw offer/respond, resign w/ confirm, result card with Elo delta). **Verified live: browser (magnus_dev) vs scripted WS client (hikaru_dev) played a full rated 5+0 — Scholar's mate, +20/−20 Elo, both sides consistent**
- [x] 4.9 REST + UI: Archive page (result/TC/reason/delta rows, PGN download); spectate-by-link deferred to Phase 7 (friends)
- [x] 4.10 WS integration tests: 2-client scripted fool's mate w/ Elo assertions, illegal/out-of-turn rejection, flag fall, resignation (4 scenarios; reconnect scenario TODO). **Test-rig lesson: all WS sessions must share ONE portal loop — open sockets from a single entered TestClient with explicit Cookie headers.** pytest-timeout (90s) now default
- [ ] 4.11 Load sanity: 50 concurrent games (do with Docker/real setup at 0.11)

**DoD:** two browsers play a full rated blitz game with correct clocks, result, and Elo updates; history shows the game with PGN.

---

## Phase 5 — Engine service, bots & review (modes 2 + 3)

- [~] 5.1 Engine service: stockfish UCI pool (async python-chess, ENGINE_POOL_SIZE=2), /botmove /analyse /review, acquire timeout → 503. **Verified live in container (level-8 opens e4; analysis finds Nf6 defense).** Still todo: priority lanes, Prometheus metrics on the engine app
- [x] 5.2 Bot levels 1–8 (skill/depth/time caps + blunder_p randomness for 1–3) in `engine/app/main.py`; anchor Elo table (600→2300) in `backend/app/chess/engine_client.py`
- [x] 5.3 Bot Arena: POST /api/v1/games (BOT/LEARN modes), bot driver (engine call outside the game lock), anchor-Elo at game end, lobby UI (opponent toggle + level picker 1–8). **Verified live vs real Stockfish through nginx: bot played the Scandinavian; resignation → −30 BOT Elo; move_events rows show user_id=human / NULL=bot in TimescaleDB.** 2026-07-22 fix: `drive_bot` now waits a human-like `_bot_think_seconds` (scaled by level, capped to ~6% of the bot's clock) BEFORE applying — the move is charged to the bot's clock, so timed bot games are no longer one-sided (bot used to reply for free). Live-verified: bot clock ticked down ~1–2s/move in a 3+2 Learn game.
- [x] 5.4 Review pipeline: Celery task `review.generate` (Redis broker; inline fallback when no broker for SQLite dev), engine /review computes per-ply win%-drop tags + lichess-formula accuracy; Archive UI: request→poll→accuracies+tagged moves. **Verified live: real worker+Stockfish returned 96.8%/91.3%.** *Eval-graph + click-through board UI deferred to Phase 8 profile work*
- [x] 5.5 Learn-by-Playing: `coach:info` after every ply (eval, win%-drop tag), baseline eval on rejoin; human=white; engine math shared with review so live and post-game tags agree. 2026-07-22 fix: `coach:info` now carries `moved_by`; the client keeps the human's move verdict + hint arrow on screen and only refreshes the eval bar on the bot's (tagless) reply — the verdict used to be wiped the instant the bot moved. Live-verified: "good" tag + gold hint arrow persisted through the bot's reply in a Guided (L2) game.
- [x] 5.6 Coach L1–L5 config-driven in `services/coach.py` (single `build_info` filter); hints/takebacks budgets tracked on LiveGame
- [x] 5.7 Coach UI (`CoachPanel`): eval readout (L1/L2 always, L3 toggle), tag chips w/ L1 explanations, hint button+arrow+counter, takeback (server rewinds 2 plies), **L1 premove blunder-confirm ("the coach winces") — all verified live vs real Stockfish through nginx :8080**
- [x] 5.8 L5 critical ping: |win% swing| ≥15 → neutral "critical moment" (build_info)
- [~] 5.9 Degradation: EngineUnavailable → bot move logged+skipped (retriggered on rejoin), coach silently skips, review 404s politely; **self-healing engine pool (respawn on EngineTerminatedError) + illegal-position 400 guard — a segfaulted stockfish corpse was poisoning the pool (exit -11). Alert metric → Phase 9**
- [x] 5.10 Tests: 37 backend (coach level matrix, tags/hints/takeback flow, premove verdicts, review inline pipeline — all vs scripted fake engine) + 6 engine-container tests vs REAL stockfish (legal botmove ×8 levels, analyse, review tags 2.g4?? as blunder). Dev-compose now mounts engine/tests; vite watcher needs VITE_POLL=1 on Windows bind mounts (fixed in compose)

**DoD:** play L1 coached game and see hints/warnings work; beat bot 1 in arena and see bot-Elo change; finished games get reviews with accuracy.

---

## Phase 6 — Learning path gating & admin CMS

- [x] 6.1 Gating: strict-linear service already shipped in Phase 3 (learn router); linear order naturally enforces "beat the stage boss (order_idx 90, last in stage) to reach the next stage." Admin bypass confirmed live.
- [x] 6.2 Boss checkpoints: `boss_config` (start_fen, bot_level, player_color, objective win|checkmate|draw|convert, move_limit, time_control); `services/boss.py` verifies from the FINISHED Game row (survives restart); `/learn/items/{slug}/boss/start` (creates BOT game, human either color) + `/boss/verify` (marks DONE on pass); `/complete` refuses bosses (409). Game service generalized: bot plays either color, custom start_fen, side-aware Elo. 12 bosses seeded (K+Q mate, K+P convert, Philidor-style draw-hold as black, beat-Bot-N ×9). **Verified live: boss briefing → Begin → real K+Q vs K board loads.**
- [x] 6.3 Boss UI (`BossChallenge`): parchment briefing (objective/color/bot), Begin → reuses GameScreen, on game-over auto-verifies and shows pass/fail + retry; 👑 styling in path
- [x] 6.4 Progress events → XP hooks: done in Phase 8 — item/boss completion calls `gamification.on_event`, awarding XP + evaluating achievements
- [x] 6.5 Admin CMS content list: stages (with item counts + draft badges) → items (live/draft badges), new-item, per-stage; `admin_content.py` router, all audit-logged
- [x] 6.6 Admin CMS item editor: metadata form + JSON content/boss editor + **live board preview replaying steps client-side** + `/validate` (python-chess) + publish gate (422 with error list on invalid); version bump on publish. **Verified live: injected an illegal move → validator reported `line[1]: illegal move 'e2e5'` → publish blocked; fixed → published → appeared AVAILABLE in the learner path.**
- [~] 6.7 Stage editor (create/patch stage) + counts done; completion-funnel stats deferred to Phase 8 analytics
- [ ] 6.8 New-content authoring batch 1 (from CURRICULUM.md backlog): Stage 1–4 gaps (~15 items) — **not started; systems are ready (CMS + validator), this is pure content authoring. Can be done incrementally via the admin UI or a seed batch.**
- [ ] 6.9 New-content authoring batch 2: Stage 5–8 gaps (~15 items)
- [ ] 6.10 New-content authoring batch 3: Stage 9–12 gaps (~12 items) — all validator-clean
- [x] 6.11 Tests: gating edge cases (locked item read/complete → 403), boss verify objective matrix (win/draw/checkmate-only/wrong-color), boss start+verify+DONE flow, CMS RBAC + publish-gate + reorder. 45 backend tests total, all green.

**DoD:** ✅ boss checkpoint fights + verify work (K+Q mate boss live-verified through the UI); ✅ admin authors→validates→publishes a drill end-to-end from the browser and it appears in the learner path; content-authoring backlog (6.8–6.10) is the remaining work and is now pure data entry on finished machinery.

---

## Phase 7 — Social: friends, presence, challenges + Mode 4 Puzzle Duel

- [x] 7.1 Friend API (`services/friends.py` + router): request/accept/decline/remove/block/unblock, one-row-per-pair, mutual-request auto-accept, block precedence, user search with relation tags; audit-logged
- [x] 7.2 `/ws/social`: presence registry (online/in_game/in_duel/offline) fanned out to friends on connect/disconnect; friend:update nudges; auto-reconnect
- [x] 7.3 Friends UI: live search, requests inbox, friend list with presence dots + challenge/remove/block; incoming-challenge banner in Layout
- [x] 7.4 Challenge flow: friend challenge (TC + rated) via `/ws/social` → accept spawns a real online game both sides rejoin through `/ws/game` (reuses the whole Phase-4 path); handoff wired in Layout → attachGame → /play
- [x] 7.5 Duel engine (`services/duel.py`): puzzle selection by mean DUEL rating, 180s shared clock, difficulty+combo scoring, wrong-move fails puzzle & resets combo, server-authoritative board/cursor per player
- [x] 7.6 `/ws/duel`: matchmaking queue pairs players; submit/progress/opponent_progress/over; duel Elo on finish. **Live-verified: two WS clients matched, solver scored 170–0, +20/−20 duel Elo through the running server**
- [x] 7.7 Duel UI: board solve-by-click, live timer, your/opponent score cards with combo flames, opponent ticker, result screen
- [~] 7.8 Spectate friend's game — deferred (game room already supports read-only join; needs a "watch" entry point in the friends list)
- [x] 7.9 Abuse guards: block removes friendship + forbids requests both ways + hidden from search; challenges friends-only; auth rate-limits already global. (report stub deferred)
- [x] 7.10 Tests: friends state machine (request/accept, mutual auto-accept, block precedence, self-friend), duel scoring/combo/rating/matchmaking, leaderboard scope — part of 54 green backend tests

**DoD:** ✅ friends add each other with live presence; ✅ a full puzzle duel finishes with correct scores + duel Elo (verified live, 170–0, ±20). Puzzle bank: 12 puzzles seeded from validated drills (Lichess CSV import still optional, TASKS 2.7).

---

## Phase 8 — Gamification

- [x] 8.1 XP ledger (`services/gamification.py`) → xp_events hypertable; level curve `100·(n-1)^1.6` (iterative inverse so it round-trips); `on_event()` entrypoint wired at item/boss complete (learn router), game win/draw/loss (ws game over, Online+Bot; Learn unrated), duel result (ws duel over), daily-streak + achievement bonuses
- [x] 8.2 Streak service: daily activity, +1/day, weekly freeze token covers one missed day; streak chip in sidebar + profile
- [x] 8.3 Achievement engine: condition_json evaluated from durable domain data (correct even if an event is missed), idempotent unlock, XP bonus; elegant toast (XP + unlock, no confetti). **Fixed a real bug found live: `_count_items_done` wasn't user-scoped → another user's drill unlocked your badge; added regression test**
- [x] 8.4 40 achievements already seeded in Phase 2; engine evaluates the item/stage/game/duel/streak/level/bot families (theme-count, combo, comeback, time-of-day left as future no-ops — documented in code)
- [x] 8.5 Leaderboards shipped in Phase 7 (online/bot/duel, global/friends). Redis caching → Phase 9
- [~] 8.6 Profile v2: level ring + XP bar, per-mode ratings, rating sparkline from rating_history hypertable, streak, achievement showcase. Accuracy trend + opening stats deferred (need player_accuracy_weekly cagg wiring + PGN aggregation)
- [x] 8.7 XP summary: reward toasts ("+N XP · Level up ✦ · Achievement unlocked") on lesson/drill/boss complete, game over (ws xp:update), and duel over
- [x] 8.8 Tests: level-curve monotonicity/round-trip, lesson-complete XP + first-steps unlock, achievements endpoint reflects unlocks, streak increments across days, **user-scoped counting regression**, stats shape — 6 new tests; 60 backend total, all green

**DoD:** ✅ verified live — completing a lesson fires +XP + "First Steps" toast, sidebar shows level/streak, Profile shows ratings/streak/showcase, Achievements page reads 2/40 with correct locked/unlocked. (Accuracy-trend + opening-stats are the one deferred slice of 8.6.)

---

## Phase 9 — Production hardening & deployment

- [x] 9.1 GitHub Actions CI (`.github/workflows/ci.yml`): backend (ruff+mypy+pytest), engine (real Stockfish), frontend (eslint+build+vitest), e2e (compose stack + Playwright), docker-build → GHCR push on main. YAML validated
- [x] 9.2 docker-compose.prod.yml: prod image targets, ModSecurity/CRS WAF terminating TLS, resource limits, restart policies, json-file log rotation, no dev mounts — `config` validates
- [x] 9.3 `prod/nginx-tls.conf`: HTTP→HTTPS redirect + ACME path, TLS1.2/1.3, HSTS preload + full security-header set + locked CSP, /metrics denied, /grafana sub-path; certbot webroot flow in RUNBOOK
- [x] 9.4 `prod/backup.sh` nightly pg_dump + gzip + 7-day rotation; tested restore procedure + cron in RUNBOOK
- [x] 9.5 Monitoring as code: Prometheus scrape + `alerts.yml` (5xx/p95/backend-down); Grafana provisioned datasources (Prometheus + **TimescaleDB**) + dashboard mixing infra RED + game telemetry (moves/engine-latency/active-players/XP/rating). **Verified live: 2 targets UP, dashboard queries hypertables (138 moves)**
- [x] 9.6 Playwright e2e (`frontend/e2e/`): register→complete lesson→earn XP, and login→Play lobby. **Both pass live against :8080**; wired into CI as its own job. **2026-07-26: fixed the CI e2e job — it had never passed.** The compose `frontend` service bind-mounts `frontend/` and runs `npm install` as root, so the runner's `npm ci` died on `EACCES rmdir node_modules` (exit 243). Added an anonymous `/app/node_modules` volume: container and host now keep separate dependency trees
- [x] 9.7 k6 load-sanity script (`devops/loadtest/browse.js`): 200-VU ramp, p95<800ms + <1% error thresholds; `make loadtest`. (Run on a deploy box, not this laptop — documented)
- [x] 9.8 SECURITY.md (secrets, authN/Z, web hardening); `.env.example` complete; **git-history secret scan clean** (.env untracked, no hard-coded secrets)
- [~] 9.9 Deploy: full VPS deploy guide + smoke steps in RUNBOOK; actual deploy pending the owner's box/domain
- [x] 9.10 Portfolio README: mermaid architecture diagram, stack table, telemetry story, quick-start, "what I'd do next"; MIT LICENSE
- [ ] 9.11 Stretch (optional): Vault, k8s/helm, Chess960 castling, game chat — intentionally left

**DoD:** CI-gated ✓, prod stack defined (TLS/WAF/limits) ✓, monitored ✓ (Grafana live on real telemetry), backed up ✓ (script+runbook), e2e green ✓. Actual public deploy is the one owner-gated step (needs a box + domain).
