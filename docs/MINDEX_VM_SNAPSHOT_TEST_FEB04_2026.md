# MINDEX VM Snapshot Test Procedure - February 4, 2026

## Overview

This document describes the manual test procedure for verifying MINDEX VM snapshots and restore functionality.

---

## Prerequisites

- Access to Proxmox host (192.168.0.100)
- SSH access to MINDEX VM (192.168.0.189)
- NAS mount configured for backups

---

## Snapshot Creation Test

### Step 1: Verify Current State

```bash
# SSH to MINDEX VM
ssh mycosoft@192.168.0.189

# Check all services running
docker ps
# Expected: postgres, redis, qdrant, mindex-api, ledger-service, registry-service

# Get current data counts
docker exec mindex-postgres psql -U mindex -d mindex -c "
SELECT 
  (SELECT COUNT(*) FROM ledger.entries) as ledger_entries,
  (SELECT COUNT(*) FROM registry.systems) as registry_systems,
  (SELECT COUNT(*) FROM graph.nodes) as graph_nodes;
"
```

### Step 2: Create Test Data

```bash
# Write test memory entry via API
curl -X POST http://localhost:8001/api/memory/write \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "system",
    "namespace": "snapshot_test",
    "key": "marker",
    "value": {"test_id": "snapshot-2026-02-04", "timestamp": "'$(date -Iseconds)'"}
  }'

# Verify it was written
curl http://localhost:8001/api/memory/read/system/snapshot_test/marker
```

### Step 3: Create Snapshot

```bash
# From Proxmox host
ssh root@192.168.0.100

# Create snapshot
pvesh create /nodes/proxmox/qemu/105/snapshot \
  --snapname "test-$(date +%Y%m%d%H%M)" \
  --description "Pre-restore test snapshot"

# List snapshots
pvesh get /nodes/proxmox/qemu/105/snapshot
```

---

## Snapshot Restore Test

### Step 1: Modify Data (Simulate Changes)

```bash
# SSH to MINDEX VM
ssh mycosoft@192.168.0.189

# Add additional data
curl -X POST http://localhost:8001/api/memory/write \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "system",
    "namespace": "snapshot_test",
    "key": "after_snapshot",
    "value": {"created": "after snapshot"}
  }'

# Verify both entries exist
curl http://localhost:8001/api/memory/list/system/snapshot_test
# Expected: ["marker", "after_snapshot"]
```

### Step 2: Rollback to Snapshot

```bash
# From Proxmox host (VM must be stopped first)
ssh root@192.168.0.100

# Stop VM
pvesh create /nodes/proxmox/qemu/105/status/stop

# Rollback to snapshot
pvesh create /nodes/proxmox/qemu/105/snapshot/test-YYYYMMDDHHMM/rollback

# Start VM
pvesh create /nodes/proxmox/qemu/105/status/start
```

### Step 3: Verify Restore

```bash
# Wait for VM to boot (~30 seconds)
sleep 30

# SSH to MINDEX VM
ssh mycosoft@192.168.0.189

# Check services
docker ps

# Verify data state
curl http://localhost:8001/api/memory/list/system/snapshot_test
# Expected: ["marker"] (after_snapshot should NOT exist)

# Verify original marker exists with correct value
curl http://localhost:8001/api/memory/read/system/snapshot_test/marker
```

---

## Database Backup Test

### Step 1: Create Backup

```bash
# SSH to MINDEX VM
ssh mycosoft@192.168.0.189

# Create PostgreSQL backup
docker exec mindex-postgres pg_dump -U mindex mindex > /opt/mycosoft/ledger/backup-$(date +%Y%m%d).sql

# Verify backup file
ls -la /opt/mycosoft/ledger/backup-*.sql

# Check backup size (should be > 1KB if data exists)
du -h /opt/mycosoft/ledger/backup-*.sql
```

### Step 2: Restore from Backup

```bash
# Drop and recreate database (careful - destructive!)
docker exec mindex-postgres psql -U mindex -d postgres -c "DROP DATABASE mindex;"
docker exec mindex-postgres psql -U mindex -d postgres -c "CREATE DATABASE mindex;"

# Restore from backup
docker exec -i mindex-postgres psql -U mindex mindex < /opt/mycosoft/ledger/backup-YYYYMMDD.sql

# Verify data restored
curl http://localhost:8001/api/registry/stats
```

---

## File Ledger Backup Test

### Step 1: Verify File Ledger

```bash
# SSH to MINDEX VM
ssh mycosoft@192.168.0.189

# Check ledger file exists
ls -la /opt/mycosoft/ledger/chain.jsonl

# Count entries
wc -l /opt/mycosoft/ledger/chain.jsonl

# View last 5 entries
tail -5 /opt/mycosoft/ledger/chain.jsonl | jq .
```

### Step 2: Verify NAS Backup

```bash
# Check NAS mount
df -h | grep nas

# Verify backup on NAS
ls -la /mnt/nas/mycosoft/ledger/

# Compare local and NAS file
diff /opt/mycosoft/ledger/chain.jsonl /mnt/nas/mycosoft/ledger/chain.jsonl
```

---

## Expected Test Results

| Test | Expected Outcome |
|------|------------------|
| Create Snapshot | Snapshot appears in Proxmox list |
| Restore Snapshot | Data reverts to snapshot state |
| PostgreSQL Backup | SQL file > 1KB on NAS |
| File Ledger Backup | JSONL file synced to NAS |
| Service Recovery | All containers auto-start |

---

## Troubleshooting

### Snapshot Creation Fails

```bash
# Check disk space on Proxmox
df -h /var/lib/vz

# Check VM disk format (must support snapshots)
pvesh get /nodes/proxmox/qemu/105/config | grep scsi0
```

### Services Don't Start After Restore

```bash
# Check Docker status
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Start containers manually
cd /opt/mycosoft && docker compose up -d
```

### NAS Mount Issues

```bash
# Check mount status
mount | grep nas

# Remount
sudo mount -a

# Check credentials file
cat /etc/samba/nas-credentials
```

---

## Automation

The snapshot schedule is automated via cron on the Proxmox host:

```bash
# View cron job
crontab -l | grep snapshot

# Expected entry:
# 0 2 * * * /opt/scripts/snapshot-schedule.sh >> /var/log/mindex-snapshot.log 2>&1
```

---

## Related Documentation

- [MINDEX VM Spec](../infra/mindex-vm/MINDEX_VM_SPEC_FEB04_2026.md)
- [Cryptographic Integrity](./CRYPTOGRAPHIC_INTEGRITY_FEB04_2026.md)
- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
