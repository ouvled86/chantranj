# RUNBOOK — Shantranj (operations)

Practical operations for the production stack. Dev workflow lives in the README.

## Stacks

- **Dev:** `devops/compose/docker-compose.dev.yml` — hot-reload, seeded, monitoring on
  `:9090`/`:3001`, Adminer on `:8081`. `make up`.
- **Prod:** `devops/compose/docker-compose.prod.yml` — prod image targets, ModSecurity/CRS
  WAF terminating TLS on `:443`, resource limits, no source mounts. `make prod-up`.

## First deploy (VPS / campus box)

Prereqs: Docker + Compose v2, a domain A-record → the box, ports 80/443 open.

```bash
git clone <repo> /opt/the-study && cd /opt/the-study
cp .env.example .env && edit .env          # secrets: SECRET_KEY, POSTGRES_*, GOOGLE_*, STUDY_DOMAIN, GRAFANA_PASSWORD
# 1. issue TLS certs (see "TLS" below) into devops/compose/prod/certs/
# 2. bring the data plane up first so migrations can run
make prod-up
docker compose -f devops/compose/docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f devops/compose/docker-compose.prod.yml exec backend python -m app.db.seed   # curriculum/puzzles/achievements
```

Smoke test: `curl -fsS https://<domain>/api/v1/../healthz` via the app, register a user, play a
bot game, open `/grafana/`.

## TLS

Certs are mounted read-only into the WAF/nginx container at `/etc/nginx/certs`
(`fullchain.pem` + `privkey.pem`). Issue with certbot using the shared webroot volume:

```bash
docker run --rm -v the-study-prod_certbot-webroot:/var/www/certbot \
  -v $PWD/devops/compose/prod/certs:/etc/letsencrypt/live/out \
  certbot/certbot certonly --webroot -w /var/www/certbot -d "$STUDY_DOMAIN"
```

Renewal: a monthly cron re-runs the above and `docker compose ... exec waf nginx -s reload`.
HSTS is preloaded, so certs must not lapse.

## Backups

- Nightly: `devops/prod/backup.sh` (cron `0 3 * * *`) → `backups/study-<ts>.sql.gz`, 7-day rotation.
- **Restore (tested procedure):**
  ```bash
  gunzip -c backups/study-<ts>.sql.gz | \
    docker compose -f devops/compose/docker-compose.prod.yml exec -T timescaledb \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  ```
  For a clean restore, drop+recreate the DB first, then `alembic upgrade head` is NOT needed
  (the dump carries schema). Verify hypertables survived:
  `SELECT hypertable_name FROM timescaledb_information.hypertables;`

## Common operations

- **Logs:** `docker compose -f devops/compose/docker-compose.prod.yml logs -f <service>`
- **Deploy a new version:** CI pushes `ghcr.io/<owner>/{backend,engine,frontend}:<sha>` on
  merge to main. On the box: set `TAG=<sha>` in `.env`, `make prod-up` (pulls + recreates),
  then `alembic upgrade head` if migrations changed.
- **Run migrations:** `... exec backend alembic upgrade head`
- **Celery not picking up new tasks:** restart the `worker` service (no autoreload in prod).
- **Engine saturated / crashed:** the pool self-heals (respawns dead Stockfish); if latency
  alerts fire, raise `ENGINE_POOL_SIZE` and the engine CPU limit.

## Monitoring

- Grafana at `/grafana/` (admin / `GRAFANA_PASSWORD`). Provisioned dashboard **"Shantranj —
  Product & Infra"**: API rate + p50/p95 latency (Prometheus), moves played, engine latency,
  active players, XP awarded, rating changes (TimescaleDB hypertables) — the automotive-
  telemetry homelab pattern applied to game data.
- Prometheus alert rules in `devops/monitoring/prometheus/alerts.yml`: 5xx rate, p95 latency,
  backend down.

## Incident quick-reference

| Symptom | First check | Likely fix |
|---|---|---|
| 502 from the app | `logs waf`, `logs backend` | backend unhealthy → `restart backend` |
| Games freeze | `logs backend` for asyncio errors | `restart backend`; check redis health |
| Bots don't move | `logs engine`; `/healthz` stockfish=true | `restart engine` |
| Reviews never finish | `logs worker`; redis reachable? | `restart worker` |
| DB disk full | TimescaleDB volume size | compression policies should run; check jobs |
