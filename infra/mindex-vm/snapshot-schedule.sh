#!/bin/bash
# Daily Proxmox VM Snapshot Script for MINDEX VM
# Created: February 4, 2026
# Runs from Proxmox host via cron

set -e

# Configuration
VM_ID="105"
VM_NAME="MINDEX-VM"
SNAPSHOT_PREFIX="daily"
MAX_SNAPSHOTS=7  # Keep 7 daily snapshots

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_NAME="${SNAPSHOT_PREFIX}_${TIMESTAMP}"

echo "=== MINDEX VM Daily Snapshot ==="
echo "Date: $(date)"
echo "VM ID: $VM_ID"
echo "Snapshot Name: $SNAPSHOT_NAME"

# Create snapshot
echo "Creating snapshot..."
qm snapshot $VM_ID $SNAPSHOT_NAME --description "Automatic daily snapshot - $(date '+%Y-%m-%d %H:%M:%S')"

if [ $? -eq 0 ]; then
    echo "SUCCESS: Snapshot created"
else
    echo "ERROR: Failed to create snapshot"
    exit 1
fi

# List existing snapshots
echo "Current snapshots:"
qm listsnapshot $VM_ID

# Cleanup old snapshots (keep only MAX_SNAPSHOTS)
echo "Checking for old snapshots to remove..."
SNAPSHOT_COUNT=$(qm listsnapshot $VM_ID | grep -c "${SNAPSHOT_PREFIX}_" || true)

if [ "$SNAPSHOT_COUNT" -gt "$MAX_SNAPSHOTS" ]; then
    # Get oldest snapshot(s) to remove
    SNAPSHOTS_TO_REMOVE=$((SNAPSHOT_COUNT - MAX_SNAPSHOTS))
    echo "Removing $SNAPSHOTS_TO_REMOVE old snapshot(s)..."
    
    qm listsnapshot $VM_ID | grep "${SNAPSHOT_PREFIX}_" | head -n $SNAPSHOTS_TO_REMOVE | while read -r line; do
        OLD_SNAPSHOT=$(echo "$line" | awk '{print $2}' | tr -d '`->')
        if [ -n "$OLD_SNAPSHOT" ] && [ "$OLD_SNAPSHOT" != "current" ]; then
            echo "Removing old snapshot: $OLD_SNAPSHOT"
            qm delsnapshot $VM_ID $OLD_SNAPSHOT || echo "Warning: Could not remove $OLD_SNAPSHOT"
        fi
    done
fi

echo "=== Snapshot Complete ==="

# Also create a database backup
echo ""
echo "=== Database Backup ==="
ssh mycosoft@192.168.0.189 'docker exec mindex-postgres pg_dump -U mycosoft mindex | gzip > /opt/mycosoft/ledger/backups/mindex_$(date +%Y%m%d).sql.gz' || echo "Warning: Database backup failed"

echo "=== All Operations Complete ==="