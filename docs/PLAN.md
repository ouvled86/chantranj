# PLAN — Shantranj: full-stack chess training platform

Master plan and decision record. Task-level detail: [TASKS.md](TASKS.md).
Technical contracts: [ARCHITECTURE.md](ARCHITECTURE.md). Content: [CURRICULUM.md](CURRICULUM.md).

## 1. Product definition

**Shantranj** — a chess improvement platform for players who know the rules and want to climb.
Not a demo: a portfolio-grade production app with real accounts, real games, real infra.

Pillars:
1. **Learn** — a gated learning path (lessons + drills, easy → hard), admin-managed content.
2. **Play** — four modes (below), all with configurable time controls and starting positions.
3. **Progress** — per-player stats, Elo per mode, XP/levels, achievements, streaks.
4. **Social** — friends, presence, challenges, head-to-head puzzle racing.

## 2. Stack decision (locked — revised 2026-07-18)

**Rationale:** the owner is a 1337 student on a DevOps internship whose current focus is a
**homelab about automotive telemetry** built on **Python + FastAPI + TimescaleDB** with a
Grafana observability layer. The chess app deliberately mirrors that stack so building it
*is* practice for the internship: same language, same database and time-series patterns, same
dashboards — different domain. Interview story: "I applied my telemetry-pipeline homelab
patterns to a real-time multiplayer product."

The **telemetry mapping** is the throughline: chess produces a natural event stream — moves,
clock ticks, engine evals, rating changes, XP events. These are written to **TimescaleDB
hypertables** and visualized in **Grafana** exactly like vehicle telemetry, with continuous
aggregates powering leaderboards and player-progress charts.

| Layer      | Choice                                                                | Matches homelab |
|------------|-----------------------------------------------------------------------|-----------------|
| Backend    | **Python 3.12 + FastAPI** (async), Pydantic v2, uvicorn/gunicorn      | ✔ identical     |
| DB         | **TimescaleDB** (PostgreSQL 16 + time-series extension)               | ✔ identical     |
| ORM / migr | **SQLAlchemy 2.0 (async, asyncpg) + Alembic**; raw SQL for hypertables/continuous aggregates | ✔ (SQL/TSDB skills) |
| Realtime   | **FastAPI native WebSockets** + **Redis pub/sub** (broadcast/fan-out across workers) | new, FastAPI-native |
| Auth       | **JWT access (15m) + rotating refresh (7d) httpOnly cookies**; passlib[bcrypt]; **Authlib** Google OAuth 2.0 | pattern-parity |
| Chess core | **python-chess** (rules, legality, PGN, UCI) — server-authoritative   | new, Python-native |
| Engine     | **Stockfish** in a dedicated `engine` container, driven via python-chess UCI | great DevOps artifact |
| Jobs/queue | **Celery + Redis** (post-game analysis, review generation, heavy engine batches) | new (recognizable DevOps skill) |
| Cache      | **Redis 7** — matchmaking queue, presence, pub/sub, rate-limit + Celery broker | shared |
| Frontend   | **React 19 + Vite + TypeScript + Tailwind 4**, react-router 7, Vitest (unchanged from v1) | — (not the learning focus) |
| Infra      | **Docker Compose (dev + prod)**, NGINX reverse proxy + TLS, Makefile  | ✔ identical     |
| Observability | **prometheus-fastapi-instrumentator → Prometheus → Grafana**; Grafana also charts game telemetry from TimescaleDB | ✔ identical (owner's specialty — showcase it) |
| Tooling    | **uv** (deps/venv), **Ruff** (lint+format), **mypy** (types), **pytest** + pytest-asyncio + httpx + **testcontainers** | modern Python std |
| CI/CD      | **GitHub Actions**: ruff → mypy → pytest → build → docker build/push  | new             |

Explicitly rejected:
- **Node/Express/Prisma/Socket.IO** (the first draft of this plan) — that mirrored the owner's
  *older* ft_transcendence project, not what they're mastering now. Fully replaced.
- **Django / Flask** — FastAPI is what the owner is learning; async + Pydantic + OpenAPI fit a
  realtime API best.
- **SQLModel** — tempting (same author as FastAPI, less boilerplate) but plain **SQLAlchemy 2.0
  + Alembic** is more transferable for internships and makes TimescaleDB-specific DDL
  (hypertables, continuous aggregates, retention/compression policies) easier to manage.
- **InfluxDB / QuestDB** — considered for telemetry, but TimescaleDB (owner's pick) keeps ONE
  database for both relational (users/games) and time-series data.
- **ARQ** instead of Celery — lighter and async-native, but Celery is far more widely
  recognized by employers; noted as a possible later swap.
- **Glicko-2** — correct long-term, but Elo is simpler to implement, explain, and migrate from.
  v1 ships Elo (K=40 provisional <30 games, K=20 after).
- **WASM Stockfish in the API process** — engine gets its own container so it can be
  resource-limited, scaled, and monitored independently (real DevOps thinking).

## 3. Game modes (locked)

All modes share: time controls (bullet 1+0, blitz 3+2 / 5+0, rapid 10+5 / 15+10, classical 30+0,
custom base+increment, or untimed) and starting position (standard, custom FEN with validation,
curriculum position picker, or Chess960/random).

### Mode 1 — Play Online
Human vs human. Matchmaking queue (rating-banded) or direct friend challenge.
**No live review of any kind** — clean competitive play. Post-game engine review available
after the game ends. Rated (online Elo) or casual toggle. Draw offers, resignation,
reconnection grace (30s), spectator link for friends.

### Mode 2 — Learn by Playing (bots with live coaching)
Bot opponent + live review, with **coaching intensity L1–L5** (information decreases as level rises):

| Level | Name       | Eval bar | Hints                  | Threat highlights | Move feedback            | Takebacks |
|-------|------------|----------|------------------------|-------------------|--------------------------|-----------|
| L1    | Full Coach | always   | best-move arrow on demand, blunder warning BEFORE confirming | always | every move, explained | unlimited |
| L2    | Guided     | always   | 5/game                 | after opponent moves | every move, tagged (✦ great … ?? blunder) | 3 |
| L3    | Balanced   | on demand| 3/game                 | off               | your moves only, tagged  | 1 |
| L4    | Whisper    | off      | none                   | off               | blunder alert AFTER the move only | 0 |
| L5    | Shadow     | off      | none                   | off               | a neutral "critical moment" ping only | 0 |

Coaching level is independent from **bot strength 1–8** (Stockfish skill-level + depth caps;
levels 1–3 also use weighted-random move selection for human-like blunders).

### Mode 3 — Bot Arena (no training wheels)
Same bots 1–8, zero assistance, rated with separate bot-arena Elo. Beating each bot level
grants achievements; bot 8 defeat = "Giant Slayer". Post-game review available.

### Mode 4 — Puzzle Duel *(the "cool" pick)*
Real-time head-to-head tactics race: both players get the same 10-puzzle gauntlet
(server-selected by rating), 3 minutes; correct = +points scaled by puzzle difficulty +
combo streak bonus, wrong = combo reset. Play vs friend or matchmade. Separate duel rating,
weekly leaderboard. Chosen because it exercises the friend system, the WebSocket layer, the puzzle bank
from the curriculum, and gamification all at once — and it's genuinely fun/addictive.

## 4. Learning path (summary — full spec in CURRICULUM.md)

- 12 stages, easy → hard, each ending in a **boss checkpoint** (scripted position vs bot with a
  required outcome, e.g. "convert K+Q vs K in 20 moves without stalemate").
- Linear gating for normal users: an item unlocks when the previous is complete; a stage
  unlocks when the previous stage's boss is beaten. Admins bypass gating.
- All 27 v1 items are reused as seed content, redistributed into the new stages.
- Content is DB-driven; **admin-only CMS** (role=ADMIN): create/edit/reorder/publish lessons,
  drills, puzzles, boss configs; draft→published workflow; JSON step editor with board preview
  and legality validation before publish.

## 5. Gamification (summary)

- **XP + levels:** XP for lessons, drills, wins, puzzles, streaks; level curve `xp = 100·n^1.6`.
- **Elo ratings:** separate for online / bot arena / puzzle duel. Provisional badge <30 games.
- **Achievements:** ~40 at launch across Learning, Tactics, Playing, Social, Dedication
  (list in TASKS.md P8). Server-side awarding via event bus (no client trust).
- **Streaks:** daily activity streak with freeze token (1/week) — drives retention.
- **Profile:** rating graphs, W/L/D, accuracy from reviews, favorite openings (from game data),
  achievement showcase.
- **Leaderboards:** global + friends-only, per rating and weekly duel points.

## 6. Delivery phases

Ordered to always keep a demoable app (each phase ends deployable):

0. Monorepo scaffold, git, tooling, compose skeleton
1. Backend foundation: auth (email+Google), users, roles, admin skeleton, metrics
2. Full DB schema (SQLAlchemy + telemetry hypertables) + v1 content migrated to seeds
3. Frontend foundation: React port of v1 design + lesson/drill player, auth UI
4. Mode 1 online play (server-authoritative games, timers, Elo)
5. Engine container; modes 2 + 3 (bots, coaching levels, post-game review)
6. Learning path gating + admin CMS + boss checkpoints
7. Friends/presence/challenges + Mode 4 Puzzle Duel
8. Gamification layer (XP, achievements, streaks, leaderboards, profile)
9. Production hardening: CI/CD, WAF, TLS, backups, e2e, load sanity, deploy + runbook

Realistic effort at ~1 session/phase for 0–3, 2 sessions for 4–7 each, 1–2 for 8–9:
**≈ 14–16 working sessions.**

## 7. Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-18 | ~~Stack mirrors The Hive (Express/Prisma/Socket.IO)~~ **SUPERSEDED** | First draft mirrored the wrong (older) project |
| 2026-07-18 | **Stack mirrors the automotive-telemetry homelab: Python/FastAPI/TimescaleDB/Grafana** (see §2) | Matches what the owner is CURRENTLY mastering on their internship |
| 2026-07-18 | TimescaleDB as the single primary DB (relational + time-series) | Owner's focus DB; one store for users/games AND telemetry hypertables |
| 2026-07-18 | Game events modeled as a telemetry stream → hypertables → Grafana | Direct, honest mirror of the homelab; makes the app real practice |
| 2026-07-18 | SQLAlchemy 2.0 + Alembic over SQLModel | More transferable; easier TimescaleDB DDL management |
| 2026-07-18 | Celery + Redis for jobs over ARQ | Employer recognizability; ARQ noted as later swap |
| 2026-07-18 | Elo over Glicko-2 for v1 | Simplicity, explainability; migration path noted |
| 2026-07-18 | Stockfish in own container, driven via python-chess UCI | Resource isolation, scaling story, DevOps showcase |
| 2026-07-18 | Mode 4 = Puzzle Duel | Max overlap with friends/realtime/gamification; fun |
| 2026-07-18 | Frontend stays React (port v1 design), content → DB seeds | Frontend isn't the learning focus; v1 design/content is the source of truth |
| 2026-07-18 | Redis added (matchmaking/presence/pub-sub/Celery broker) | Needed for realtime scaling; industry-standard |
