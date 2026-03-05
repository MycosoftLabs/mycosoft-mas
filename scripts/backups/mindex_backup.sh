#!/bin/bash
# mindex_backup.sh - Hourly pg_dump of MINDEX PostgreSQL
# Run on MINDEX VM (189) or host with network access to Postgres. Retention: 24 hours.
#
# Usage:
#   ./mindex_backup.sh
#
# Env (or .env):
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
#   Or: MINDEX_DB_HOST, MINDEX_DB_PORT, MINDEX_DB_USER, MINDEX_DB_PASSWORD, MINDEX_DB_NAME
#
# Crontab (hourly):
#   0 * * * * /opt/mycosoft/scripts/backups/mindex_backup.sh >> /var/log/mycosoft/mindex_backup.log 2>&1
#
# Restore:
#   gunzip -c /opt/mycosoft/backups/mindex/mindex_YYYYMMDD_HH.sql.gz | psql -U mycosoft -d mindex

set -e

BACKUP_BASE="${MINDEX_BACKUP_DIR:-/opt/mycosoft/backups/mindex}"
RETENTION_HOURS="${MINDEX_BACKUP_RETENTION_HOURS:-24}"
PGHOST="${PGHOST:-${MINDEX_DB_HOST:-localhost}}"
PGPORT="${PGPORT:-${MINDEX_DB_PORT:-5432}}"
PGUSER="${PGUSER:-${MINDEX_DB_USER:-mycosoft}}"
PGPASSWORD="${PGPASSWORD:-${MINDEX_DB_PASSWORD}}"
PGDATABASE="${PGDATABASE:-${MINDEX_DB_NAME:-mindex}}"

if [ -z "${PGPASSWORD}" ]; then
  echo "ERROR: PGPASSWORD or MINDEX_DB_PASSWORD must be set" >&2
  exit 1
fi

mkdir -p "${BACKUP_BASE}"
TIMESTAMP=$(date +%Y%m%d_%H)
BACKUP_FILE="${BACKUP_BASE}/mindex_${TIMESTAMP}.sql.gz"

echo "[$(date -Iseconds)] Starting MINDEX backup to ${BACKUP_FILE}"
PGPASSWORD="${PGPASSWORD}" pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
  --no-owner --no-acl | gzip -9 > "${BACKUP_FILE}"
echo "[$(date -Iseconds)] Backup complete ($(du -h "${BACKUP_FILE}" | cut -f1))"

# Prune backups older than retention (in hours)
find "${BACKUP_BASE}" -name "mindex_*.sql.gz" -mmin +$((RETENTION_HOURS * 60)) -delete 2>/dev/null || true
echo "[$(date -Iseconds)] Pruned backups older than ${RETENTION_HOURS}h"
