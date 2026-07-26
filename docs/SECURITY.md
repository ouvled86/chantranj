# SECURITY — Shantranj

## Secrets

- All secrets come from a host `.env` (see `.env.example` for the full list). `.env` is
  git-ignored; secrets are **never** baked into images (Dockerfiles copy source only, config
  is read from the environment at boot via pydantic-settings).
- Required in prod: `SECRET_KEY` (long random), `POSTGRES_PASSWORD`, `GRAFANA_PASSWORD`,
  and — if Google sign-in is enabled — `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.
- Generate a key: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- Rotation: change `SECRET_KEY` to invalidate all sessions (access + refresh); rotate DB and
  Grafana passwords via their respective services and update `.env`.
- No secret has ever been committed — history was scanned (see below). If one ever is, rotate
  it and purge with `git filter-repo`.

## AuthN / AuthZ

- Passwords: bcrypt (per-password salt). Min 8 chars, letter+digit enforced server-side.
- JWT access token (15 min) + rotating refresh token (7 days) in httpOnly, SameSite=Lax,
  Secure (prod) cookies. Refresh tokens are stored **hashed**; rotation with reuse detection
  revokes the whole token family on replay.
- RBAC: `USER` / `ADMIN`; admin routes require the role and are audit-logged.

## Web hardening

- CSRF: double-submit token on cookie-authenticated state-changing requests.
- Security headers at the edge (nginx) and app: HSTS (preload), X-Content-Type-Options,
  X-Frame-Options DENY, Referrer-Policy, a locked-down CSP, Permissions-Policy.
- WAF: OWASP ModSecurity Core Rule Set in front of the app in prod.
- Rate limiting: auth endpoints 5/min/IP, general 100/min/user (Redis-backed, in-proc fallback).
- CORS locked to the configured frontend origin.
- `/metrics` is never exposed publicly (nginx denies it; Prometheus scrapes it on the internal
  network only).
- All chess legality and game state is server-authoritative (python-chess); the client cannot
  forge moves, clocks, or results.

## Dependencies & CI

- CI runs ruff + mypy (strict) + pytest on the backend/engine and eslint + build + vitest on
  the frontend for every PR. Dependabot/`uv`/`npm audit` recommended as a follow-up.

## Reporting

This is a portfolio project; for real deployments, add a `security.txt` and a contact address.
