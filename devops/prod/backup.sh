#!/usr/bin/env sh
# Nightly TimescaleDB backup with 7-day rotation. Run from cron on the host:
#   0 3 * * *  cd /opt/the-study && sh devops/prod/backup.sh >> /var/log/study-backup.log 2>&1
set -eu

COMPOSE="docker compose -f devops/compose/docker-compose.prod.yml"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="backups/study-${STAMP}.sql.gz"

mkdir -p backups
echo "[$(date -Is)] dumping to ${OUT}"
$COMPOSE exec -T timescaledb \
  pg_dump -U "${POSTGRES_USER:-study}" -d "${POSTGRES_DB:-study}" \
  | gzip > "${OUT}"

# Keep the last 7 dumps.
ls -1t backups/study-*.sql.gz | tail -n +8 | xargs -r rm -f
echo "[$(date -Is)] done; $(ls -1 backups/study-*.sql.gz | wc -l) backups retained"
