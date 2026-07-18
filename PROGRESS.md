# PROGRESS — The Study

> Live tracker. Read this first every session. Update it every time a task lands.
> Detailed checkboxes live in [docs/TASKS.md](docs/TASKS.md).

## Status snapshot

| Phase | Name                                   | Status      | Progress |
|-------|----------------------------------------|-------------|----------|
| v1    | Static lesson app (design + content)   | ✅ Shipped  | 100%     |
| P     | Planning & documentation               | ✅ Shipped  | 100%     |
| 0     | Monorepo scaffold & tooling            | ⬜ Not started | 0%    |
| 1     | Backend foundation (auth, users, admin)| ⬜ Not started | 0%    |
| 2     | Database schema & content seeding      | ⬜ Not started | 0%    |
| 3     | Frontend foundation (React port)       | ⬜ Not started | 0%    |
| 4     | Online play (mode 1)                   | ⬜ Not started | 0%    |
| 5     | Engine service, bots & review (modes 2+3) | ⬜ Not started | 0% |
| 6     | Learning path & admin CMS              | ⬜ Not started | 0%    |
| 7     | Friends, presence & Puzzle Duel (mode 4) | ⬜ Not started | 0%  |
| 8     | Gamification (XP, achievements, boards)| ⬜ Not started | 0%    |
| 9     | Production hardening & deployment      | ⬜ Not started | 0%    |

**Overall: planning complete (stack revised 2026-07-18 → Python/FastAPI/TimescaleDB) — Phase 0 in progress.**

> ⚠ Machine note (2026-07-18): dev machine has git + Node 26, but **no Docker, no Python, no uv**.
> Scaffold + frontend are verifiable locally; `make up` / backend tests need Docker Desktop
> (or Python 3.12 + uv) installed — flagged to the owner.

## What exists right now

- v1 static app at repo root: `index.html`, `js/engine.js` (move application + pseudo-legal
  movegen), `js/content.js` (27 verified lessons/drills), `js/app.js` (lesson player, drill
  player, progress via localStorage), `css/style.css` (full design token system).
- Dev server config: `.claude/launch.json` → `npx http-server -p 4173 .`
- Planning suite: `CLAUDE.md`, this file, `docs/PLAN.md`, `docs/ARCHITECTURE.md`,
  `docs/TASKS.md`, `docs/CURRICULUM.md`.
- No git repo yet (git init is task 0.1). No backend, no containers yet.

## Next up

**→ Phase 0, task 0.1:** `git init`, first commit of v1 + docs, then scaffold the monorepo
layout (`frontend/`, `backend/`, `devops/`, `docs/`) per docs/ARCHITECTURE.md §2.
Read docs/TASKS.md → "Phase 0" before starting.

## Session log

_Newest first. Keep entries to 2–4 lines._

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
