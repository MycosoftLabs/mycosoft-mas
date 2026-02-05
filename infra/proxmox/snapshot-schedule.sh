#!/bin/bash
# Mycosoft Proxmox Snapshot Schedule Script
# Created: February 5, 2026
# Run from Proxmox host via cron
#
# Cron entries to add on Proxmox host (192.168.0.202):
# 0 2 * * * /opt/mycosoft/scripts/snapshot-schedule.sh daily
# 0 3 * * 0 /opt/mycosoft/scripts/snapshot-schedule.sh weekly
# 0 4 * * * /opt/mycosoft/scripts/snapshot-schedule.sh mindex-daily
# 0 5 1 * * /opt/mycosoft/scripts/snapshot-schedule.sh monthly

set -e

# Configuration
PROXMOX_NODE="pve"
LOG_FILE="/var/log/mycosoft-snapshots.log"
DATE=$(date +%Y%m%d_%H%M%S)
DATE_SHORT=$(date +%Y%m%d)

# VM IDs
MAS_VM_ID=188
WEBSITE_VM_ID=103
MINDEX_VM_ID=189

# Retention periods (in days)
DAILY_RETENTION=7
WEEKLY_RETENTION=30
MINDEX_RETENTION=14
MONTHLY_RETENTION=365

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

create_snapshot() {
    local vm_id=$1
    local snap_name=$2
    local description=$3
    
    log "Creating snapshot: VM $vm_id - $snap_name"
    qm snapshot "$vm_id" "$snap_name" --description "$description" 2>&1 | tee -a "$LOG_FILE"
    log "Snapshot created successfully: $snap_name"
}

cleanup_old_snapshots() {
    local vm_id=$1
    local prefix=$2
    local retention_days=$3
    
    log "Cleaning up snapshots older than $retention_days days for VM $vm_id with prefix $prefix"
    
    snapshots=$(qm listsnapshot "$vm_id" 2>/dev/null | grep "$prefix" | awk '{print $1}' || true)
    
    for snap in $snapshots; do
        snap_date=$(echo "$snap" | grep -oP '\d{8}' | head -1)
        if [ -n "$snap_date" ]; then
            snap_timestamp=$(date -d "${snap_date:0:4}-${snap_date:4:2}-${snap_date:6:2}" +%s 2>/dev/null || echo "0")
            cutoff_timestamp=$(date -d "-$retention_days days" +%s)
            
            if [ "$snap_timestamp" -lt "$cutoff_timestamp" ] && [ "$snap_timestamp" -gt "0" ]; then
                log "Deleting old snapshot: $snap"
                qm delsnapshot "$vm_id" "$snap" 2>&1 | tee -a "$LOG_FILE" || true
            fi
        fi
    done
}

backup_mindex_database() {
    log "Backing up MINDEX PostgreSQL database"
    ssh mycosoft@192.168.0.189 "docker exec mindex-postgres pg_dump -U mycosoft mindex" > "/tmp/mindex_backup_${DATE_SHORT}.sql"
    scp "/tmp/mindex_backup_${DATE_SHORT}.sql" mycosoft@192.168.0.187:/mnt/mycosoft-nas/mindex/backups/
    rm -f "/tmp/mindex_backup_${DATE_SHORT}.sql"
    log "MINDEX database backup complete"
}

case "$1" in
    daily)
        log "=== Starting Daily Snapshots ==="
        create_snapshot "$MAS_VM_ID" "daily_${DATE}" "Daily container snapshot - MAS VM"
        cleanup_old_snapshots "$MAS_VM_ID" "daily_" "$DAILY_RETENTION"
        log "=== Daily Snapshots Complete ==="
        ;;
    weekly)
        log "=== Starting Weekly Snapshots ==="
        create_snapshot "$MAS_VM_ID" "weekly_${DATE}" "Weekly full VM snapshot - MAS VM"
        cleanup_old_snapshots "$MAS_VM_ID" "weekly_" "$WEEKLY_RETENTION"
        create_snapshot "$WEBSITE_VM_ID" "weekly_${DATE}" "Weekly full VM snapshot - Website Sandbox"
        cleanup_old_snapshots "$WEBSITE_VM_ID" "weekly_" "$WEEKLY_RETENTION"
        log "=== Weekly Snapshots Complete ==="
        ;;
    mindex-daily)
        log "=== Starting MINDEX Daily Backup ==="
        backup_mindex_database
        create_snapshot "$MINDEX_VM_ID" "daily_${DATE}" "Daily snapshot with DB backup - MINDEX VM"
        cleanup_old_snapshots "$MINDEX_VM_ID" "daily_" "$MINDEX_RETENTION"
        log "=== MINDEX Daily Backup Complete ==="
        ;;
    monthly)
        log "=== Starting Monthly Full Backups ==="
        create_snapshot "$MAS_VM_ID" "monthly_${DATE}" "Monthly full backup - MAS VM"
        create_snapshot "$WEBSITE_VM_ID" "monthly_${DATE}" "Monthly full backup - Website Sandbox"
        create_snapshot "$MINDEX_VM_ID" "monthly_${DATE}" "Monthly full backup - MINDEX VM"
        cleanup_old_snapshots "$MAS_VM_ID" "monthly_" "$MONTHLY_RETENTION"
        cleanup_old_snapshots "$WEBSITE_VM_ID" "monthly_" "$MONTHLY_RETENTION"
        cleanup_old_snapshots "$MINDEX_VM_ID" "monthly_" "$MONTHLY_RETENTION"
        log "=== Monthly Full Backups Complete ==="
        ;;
    agent-state)
        log "=== Creating Agent State Snapshot ==="
        create_snapshot "$MAS_VM_ID" "agent_${DATE}" "Agent state snapshot after critical task"
        cleanup_old_snapshots "$MAS_VM_ID" "agent_" 1
        log "=== Agent State Snapshot Complete ==="
        ;;
    status)
        echo "MAS VM ($MAS_VM_ID) Snapshots:"
        qm listsnapshot "$MAS_VM_ID" 2>/dev/null || echo "No snapshots"
        echo "Website Sandbox ($WEBSITE_VM_ID) Snapshots:"
        qm listsnapshot "$WEBSITE_VM_ID" 2>/dev/null || echo "No snapshots"
        echo "MINDEX VM ($MINDEX_VM_ID) Snapshots:"
        qm listsnapshot "$MINDEX_VM_ID" 2>/dev/null || echo "No snapshots"
        ;;
    *)
        echo "Usage: $0 {daily|weekly|mindex-daily|monthly|agent-state|status}"
        exit 1
        ;;
esac
exit 0
