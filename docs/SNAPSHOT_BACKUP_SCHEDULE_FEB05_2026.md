# Snapshot & Backup Schedule - February 5, 2026

## Overview

This document defines the snapshot and backup schedule for all Mycosoft infrastructure components.

## Proxmox VM Snapshots

### VM Inventory

| VM ID | Name | Purpose | Critical |
|-------|------|---------|----------|
| 188 | MAS Containers | Multi-Agent System services | Yes |
| 103 | Website | mycosoft.com website | Yes |
| 189 | MINDEX | Database and indexing | Yes |

### Snapshot Schedule

#### Daily Snapshots (2:00 AM)
```bash
# Cron entry on Proxmox host (192.168.0.202)
0 2 * * * /opt/mycosoft/scripts/snapshot-schedule.sh daily
```

**Retention**: 7 days

#### Weekly Snapshots (Sundays 3:00 AM)
```bash
0 3 * * 0 /opt/mycosoft/scripts/snapshot-schedule.sh weekly
```

**Retention**: 4 weeks

#### Monthly Snapshots (1st of month 4:00 AM)
```bash
0 4 1 * * /opt/mycosoft/scripts/snapshot-schedule.sh monthly
```

**Retention**: 12 months

#### MINDEX Database Backup (4:00 AM)
```bash
0 4 * * * /opt/mycosoft/scripts/snapshot-schedule.sh mindex-daily
```

Process:
1. SSH to MINDEX VM (192.168.0.189)
2. Execute `pg_dump` in PostgreSQL container
3. Transfer dump to NAS via SCP
4. Retain 30 days of database backups

### Backup Jobs Configuration

Located at: `infra/proxmox/backup-jobs.yml`

```yaml
backup_jobs:
  - id: daily-mas-containers
    vmid: 188
    schedule: "0 2 * * *"
    mode: snapshot
    compress: zstd
    storage: local
    retention:
      keep_daily: 7
      
  - id: daily-website
    vmid: 103
    schedule: "0 3 * * *"
    mode: snapshot
    compress: zstd
    storage: local
    retention:
      keep_daily: 7
      
  - id: daily-mindex
    vmid: 189
    schedule: "0 4 * * *"
    mode: snapshot
    pre_hook: "/opt/mycosoft/scripts/snapshot-schedule.sh mindex-daily"
    compress: zstd
    storage: local
    retention:
      keep_daily: 7
```

## NAS Backup Integration

### Mount Point
```
//192.168.0.105/mycosoft.com -> /mnt/mycosoft-nas
```

### Directory Structure
```
/mnt/mycosoft-nas/
├── dev/
│   ├── builds/
│   ├── artifacts/
│   └── logs/
├── mindex/
│   ├── backups/        # PostgreSQL dumps
│   ├── ledger/         # Integrity ledger
│   └── exports/
└── archives/
    └── 2026/
        ├── Q1/
        ├── Q2/
        ├── Q3/
        └── Q4/
```

### Backup Locations

| Data Type | Location | Retention |
|-----------|----------|-----------|
| PostgreSQL Dumps | `/mnt/mycosoft-nas/mindex/backups/` | 30 days |
| Integrity Ledger | `/mnt/mycosoft-nas/mindex/ledger/` | Permanent |
| Build Artifacts | `/mnt/mycosoft-nas/dev/builds/` | 90 days |
| Archived Data | `/mnt/mycosoft-nas/archives/2026/` | Permanent |

## Cryptographic Integrity

All backups are verified using:

1. **SHA256 Hashing**: Every file hashed before write
2. **HMAC-SHA256**: Signed with secret key
3. **Merkle Root**: Computed for sync manifests
4. **Dual-Write Ledger**: PostgreSQL + file-based

```python
from mycosoft_mas.security.nas_sync_service import NASSyncService

sync = NASSyncService("/mnt/mycosoft-nas")
result = await sync.sync_with_integrity(
    source_dir="/data/backup",
    dest_subpath="mindex/backups",
    record_in_ledger=True
)
```

## Monitoring

### Check Backup Status
```bash
/opt/mycosoft/scripts/snapshot-schedule.sh status
```

### Verify Integrity
```python
from mycosoft_mas.security.integrity_service import IntegrityService

integrity = IntegrityService()
is_valid = await integrity.verify_ledger()
```

## Disaster Recovery

### Recovery Steps

1. **Identify Failure Point**
   - Check Proxmox console for VM status
   - Review backup logs

2. **Restore VM Snapshot**
   ```bash
   qm rollback <vmid> <snapshot_name>
   ```

3. **Restore Database**
   ```bash
   # On MINDEX VM
   docker exec -i mindex-postgres psql -U mycosoft -d mindex < backup.sql
   ```

4. **Verify Integrity**
   - Run integrity verification
   - Check application health

5. **Resume Services**
   - Start containers
   - Verify health endpoints
