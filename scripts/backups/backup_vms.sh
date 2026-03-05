#!/bin/bash
# backup_vms.sh - Daily VM snapshots via Proxmox vzdump
# Run on Proxmox host. Retention: 7 days.
#
# Usage:
#   ./backup_vms.sh [--storage STORAGE]
#
# Env:
#   BACKUP_STORAGE  - Proxmox storage for backups (default: local)
#   VM_IDS          - Comma-separated VM IDs (default: 187,188,189,190,191)
#   RETENTION_DAYS  - Days to keep (default: 7)
#
# Crontab (daily at 2:00 AM):
#   0 2 * * * /opt/mycosoft/scripts/backups/backup_vms.sh >> /var/log/mycosoft/backup_vms.log 2>&1

set -e

STORAGE="${BACKUP_STORAGE:-local}"
VM_IDS="${VM_IDS:-187,188,189,190,191}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/vz/dump}"
LOG_PREFIX="[$(date -Iseconds)]"

echo "${LOG_PREFIX} Starting VM backups (storage=${STORAGE}, retention=${RETENTION_DAYS}d)"

for vmid in $(echo "${VM_IDS}" | tr ',' ' '); do
  if qm status "${vmid}" &>/dev/null || pct status "${vmid}" &>/dev/null; then
    echo "${LOG_PREFIX} Backing up VM ${vmid}..."
    vzdump "${vmid}" --storage "${STORAGE}" --compress zstd --mode snapshot
  else
    echo "${LOG_PREFIX} VM ${vmid} not found or not running, skipping"
  fi
done

# Remove backups older than retention (vzdump creates vzdump-qemu-ID-YYYY_MM_DD-HH_MN_SS.vma.zst)
echo "${LOG_PREFIX} Pruning backups older than ${RETENTION_DAYS} days..."
# Storage dump dir varies; default 'local' uses /var/lib/vz/dump. Set BACKUP_DIR if different.
find "${BACKUP_DIR}" -name "vzdump-qemu-*.vma.zst" -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true
find "${BACKUP_DIR}" -name "vzdump-qemu-*.raw" -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true

echo "${LOG_PREFIX} Backup complete."
