# ARCHITECTURE — Shantranj

Technical contracts. Keep in sync with implementation; when code and this doc disagree,
fix one of them in the same session. Stack: Python 3.12 + FastAPI + TimescaleDB (see PLAN §2).

## 1. System overview

```
                     ┌──────────────────────────── docker network ────────────────────────────┐
 browser ─https─►  nginx (TLS, static React build, /api proxy, /ws proxy)                      │
                     │        │                                                                 │
                     │        ▼                                                                 │
                     │   backend (FastAPI + uvicorn workers, WebSockets)                        │
                     │        │        │            │                                           │
                     │        ▼        ▼            ▼                                           │
                     │  timescaledb   redis      engine (Stockfish, python-chess UCI)           │
                     │   (pg16+tsdb)  (pubsub/    ▲                                              │
                     │        ▲        queue/     │                                              │
                     │        │        cache)  celery worker (review/analysis jobs)             │
                     │        │                                                                 │
                     │   prometheus ─► grafana  (infra metrics  +  game telemetry from tsdb)    │
                     └─────────────────────────────────────────────────────────────────────────┘
```

Services (compose): `nginx`, `backend` (FastAPI), `worker` (Celery), `engine`, `timescaledb`,
`redis`, `prometheus`, `grafana`. Dev compose adds `frontend` (Vite dev server) + `adminer` +
hot-reload mounts. Prod compose: nginx serves the built React `dist`, adds TLS + resource
limits + restart policies (ModSecurity WAF = stretch).

## 2. Monorepo layout

```
/
├── frontend/               # React 19 + Vite + TS + Tailwind 4 (unchanged focus)
│   └── src/{app,components,features,lib,styles}
├── backend/
│   ├── pyproject.toml      # uv-managed; ruff + mypy + pytest config
│   ├── alembic/            # migrations (incl. hypertable + continuous-aggregate DDL)
│   ├── app/
│   │   ├── main.py         # FastAPI app factory, lifespan, router + middleware wiring
│   │   ├── core/           # config (pydantic-settings), security, logging, deps
│   │   ├── db/             # engine/session, base, timescale helpers
│   │   ├── models/         # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/        # Pydantic v2 request/response models
│   │   ├── api/v1/         # routers: auth, users, friends, games, curriculum,
│   │   │                   #          puzzles, achievements, leaderboards, admin
│   │   ├── services/       # business logic (elo, gating, xp, matchmaking, review)
│   │   ├── ws/             # WebSocket endpoints + connection manager (game, social, duel)
│   │   ├── chess/          # python-chess helpers, engine client, bot policy
│   │   ├── telemetry/      # event → hypertable writers, metric emitters
│   │   └── workers/        # celery app + tasks (review, batch analysis)
│   └── tests/              # pytest (unit + integration w/ testcontainers)
├── engine/                 # FastAPI micro-service wrapping Stockfish (UCI via python-chess)
├── devops/
│   ├── compose/            # docker-compose.dev.yml, docker-compose.prod.yml
│   ├── containers/         # backend.Dockerfile, frontend.Dockerfile, engine.Dockerfile
│   ├── monitoring/         # prometheus/ (config), grafana/ (provisioned dashboards+datasources)
│   └── prod/               # nginx conf, TLS
├── docs/                   # this planning suite
├── legacy-v1/              # the static v1 app (moved in Phase 0; design + content source)
└── Makefile                # up down logs migrate seed test lint fmt build prod-up ...
```

Per-module convention (backend): a feature owns a router (`api/v1/<feat>.py`), a service
(`services/<feat>.py`), Pydantic schemas (`schemas/<feat>.py`), and shares ORM models.

## 3. Data model

### 3a. Relational (SQLAlchemy 2.0 ORM)

```
User          id, email(uq), username(uq), password_hash?, google_id?, avatar_url, role(USER|ADMIN),
              created_at, last_seen_at, settings(jsonb)
RefreshToken  id, user_id, token_hash, expires_at, revoked_at?         (rotation + reuse detection)
Rating        user_id+mode(ONLINE|BOT|DUEL) → value, games, provisional
Game          id, mode, white_id?, black_id?, bot_level?, coach_level?, time_control(jsonb),
              start_fen, pgn, result(WHITE|BLACK|DRAW|ABORTED), end_reason,
              rated, rating_delta_w/b, started_at, ended_at
GameReview    game_id, moves_analysis(jsonb: eval/best/tag per ply), accuracy_w, accuracy_b, generated_at
Friendship    requester_id, addressee_id, status(PENDING|ACCEPTED|BLOCKED), created_at  (uq pair)
Stage         id, slug, title, intro, order_idx, published
LearnItem     id, stage_id, slug, kind(LESSON|DRILL|BOSS), title, sub, order_idx,
              content_json(jsonb, v1 step/line format), boss_config?(jsonb), published, version
ItemProgress  user_id+item_id → status(LOCKED|AVAILABLE|DONE), score?, completed_at
PuzzleBank    id, fen, line(jsonb), themes(text[]), difficulty(int), source
Achievement   id, slug, title, description, icon, category, condition_json(jsonb), xp
UserAchievement user_id+achievement_id → unlocked_at
Streak        user_id → current, best, last_active_date, freezes_left
DuelMatch     id, player_a_id, player_b_id, puzzle_ids(int[]), score_a, score_b, started_at, ended_at
```

### 3b. Time-series (TimescaleDB hypertables) — the telemetry layer

These are created via Alembic with raw SQL (`create_hypertable`, compression, retention,
continuous aggregates). This is the direct mirror of the automotive-telemetry homelab.

```
move_events        time, game_id, user_id? (denormalized; null=bot), ply, side, uci, san,
                   clock_ms, eval_cp?, is_book, tag?
                   → hypertable(time); feeds live game telemetry + post-hoc accuracy
clock_ticks        time, game_id, white_ms, black_ms          (sampled; server clock truth)
rating_history     time, user_id, mode, value, delta, game_id  → hypertable; powers rating graphs
xp_events          time, user_id, amount, reason, ref_id       → hypertable (append-only ledger)
engine_samples     time, request_kind(analyse|botmove|review), depth, latency_ms, queue_depth
                   → hypertable; powers engine Grafana panels + saturation alerts
activity_events    time, user_id, kind(login|lesson|drill|game|duel|puzzle)  → drives streaks + funnels
```

Continuous aggregates (materialized, auto-refreshed; caggs can't join or COUNT DISTINCT —
hence the denormalized user_id and the two-step DAU):
- `leaderboard_daily` — last rating per user/mode per day via `last(value, time)`
- `player_accuracy_weekly` — clean-move ratio per user/week from move_events tags
- `engine_latency_5m` — avg/max latency + volume per request_kind (p95 comes from the
  Prometheus histograms on the engine service, not TimescaleDB)
- `activity_daily` — events per user per day; DAU = `count(*)` over it grouped by day

Retention/compression: compress hypertable chunks older than 7d; drop raw `clock_ticks` after
30d (aggregates persist). Derived values (level from xp_events, W/L/D from Game) are computed,
never double-stored.

## 4. HTTP API surface (REST, /api/v1) — FastAPI routers

- `POST /auth/register|login|logout|refresh` · `GET /auth/google` + `/auth/google/callback`
- `GET/PATCH /users/me` · `GET /users/{username}` (public profile) · `GET /users/me/stats`
- `GET /friends` · `POST /friends/requests` · `POST /friends/requests/{id}/accept|decline`
  · `DELETE /friends/{id}` · `POST /friends/{id}/block`
- `POST /games` (create vs bot) · `GET /games/{id}` · `GET /games?user=` (history, paginated)
  · `POST /games/{id}/review` (enqueue Celery analysis) · `GET /games/{id}/review`
- `GET /learn/path` (stages+items+my progress) · `GET /learn/items/{slug}`
  · `POST /learn/items/{slug}/complete` (server validates drill line / boss result w/ python-chess)
- `GET /puzzles/next` · `POST /puzzles/{id}/attempt`
- `GET /achievements` · `GET /leaderboards/{board}` (served from continuous aggregates)
- `GET /me/telemetry/{series}` (rating/accuracy/xp time-series for profile charts, from hypertables)
- Admin (`role=ADMIN`): CRUD `/admin/stages`, `/admin/items` (draft/publish/reorder/validate),
  `/admin/users` (list, role, ban), `/admin/metrics-summary`
- Ops: `GET /healthz` (liveness) · `GET /readyz` (db+redis+engine ping) · `GET /metrics`
  (Prometheus exposition, internal-only)

All request/response bodies are Pydantic v2 models (auto OpenAPI at `/docs`). Errors returned
as `{"error": {"code", "message", "details"?}}` via a global exception handler.

## 5. WebSocket contracts (FastAPI WebSockets + Redis pub/sub)

Three endpoints, authenticated by the JWT cookie at the handshake. A `ConnectionManager` tracks
sockets per room; cross-worker fan-out goes through Redis pub/sub so any uvicorn worker can
deliver. Messages are JSON `{type, data}`.

**`/ws/game`**
- C→S: `queue:join {mode,time_control,rated}` · `queue:leave` · `game:move {game_id,from,to,promo?}`
  · `game:resign` · `game:draw_offer` · `game:draw_respond {accept}` · `game:rejoin {game_id}`
- S→C: `queue:matched {game_id,color,opponent}` · `game:state {fen,clocks,last_move,status}`
  · `game:move` (relay + clocks) · `game:over {result,reason,rating_delta}` · `coach:info`
  (mode-2 only, per coach level) · `game:opponent_connection {connected}`

**`/ws/social`** — presence heartbeat → `friend:online|offline|in_game`,
`challenge:send|receive|accept|decline`.

**`/ws/duel`** — `duel:queue|challenge` · `duel:start {puzzles}` · `duel:submit {puzzle_idx,move}`
· `duel:opponent_progress {score,streak}` · `duel:over {scores,rating_delta}`.

Server is authoritative: every move validated with **python-chess** server-side; clocks run
server-side (monotonic `loop.time()`), client clocks are cosmetic; disconnect = 30s grace then
auto-loss (rated). Every accepted move also emits a `move_events` telemetry row.

## 6. Engine service

Container `engine`: a small FastAPI app owning a pool of Stockfish processes via
`python-chess`'s UCI transport. Internal HTTP:
- `POST /analyse {fen, depth?, multipv?}` → `{lines:[{move,eval,pv}]}`
- `POST /botmove {fen, level(1-8)}` → `{move}` (skill level + depth/time caps; weighted-random
  imperfection for levels 1–3 to feel human)
- `POST /review {pgn}` → per-ply `{eval,best,tag}` (heavier; called by Celery worker, not inline)
- `GET /healthz`

Concurrency: bounded process pool (N≈cpu), per-request timeout, two priority lanes
(interactive `botmove`/`analyse` > batch `review`) so reviews can't starve live games. Each
call emits an `engine_samples` telemetry row (latency, depth, queue depth) → Grafana.

## 7. Security & production posture

- httpOnly + secure + samesite=lax cookies; CSRF double-submit token on state-changing REST;
  WebSocket auth at handshake; refresh-token rotation with reuse detection (revoke token family).
- Passwords: passlib[bcrypt]. JWTs: python-jose/PyJWT, short access + rotating refresh.
- RBAC dependency (`require_role(ADMIN)`); admin routes IP-logged to an audit table.
- Rate limiting via Redis (slowapi or custom dependency): auth 5/min/IP, general 100/min/user,
  WS events throttled per-type. helmet-equivalent headers via middleware; CORS locked to origin.
- Config via **pydantic-settings** (env validated at boot); secrets never baked into images;
  prod secrets via host `.env` / Docker secrets.
- NGINX: TLS (Let's Encrypt), HSTS, gzip/brotli, static caching; ModSecurity CRS = stretch.
- TimescaleDB: nightly `pg_dump` volume + tested restore runbook; migrations via
  `alembic upgrade head` on deploy; compression + retention policies as above.
- Monitoring: prometheus-fastapi-instrumentator (RED metrics per route), WS connection gauge,
  Celery queue depth, engine latency histograms. Grafana dashboards provisioned as code, with a
  **TimescaleDB datasource** for game-telemetry panels alongside the Prometheus infra panels.
  Alert rules: 5xx rate, p95 latency, engine saturation, worker backlog.
- Tests: unit (services: elo, gating, xp, bot policy), integration (httpx AsyncClient +
  **testcontainers** TimescaleDB/Redis), WebSocket integration (two clients play a scripted
  game), e2e happy paths (Playwright). CI (GitHub Actions) gates ruff + mypy + pytest.
```
