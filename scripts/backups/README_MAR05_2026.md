# Backup Scripts - March 5, 2026

## Scripts

| Script | Purpose | Retention | Schedule |
|--------|---------|-----------|----------|
| `backup_vms.sh` | Proxmox VM snapshots (vzdump) | 7 days | Daily 2:00 AM |
| `mindex_backup.sh` | MINDEX PostgreSQL pg_dump | 24 hours | Hourly |

## Where to Run

- **backup_vms.sh**: On the Proxmox host (requires `qm`, `vzdump`)
- **mindex_backup.sh**: On MINDEX VM (192.168.0.189) or host with Postgres access

## Crontab Entries

```bash
# On Proxmox host
0 2 * * * /opt/mycosoft/scripts/backups/backup_vms.sh >> /var/log/mycosoft/backup_vms.log 2>&1

# On MINDEX VM
0 * * * * /opt/mycosoft/scripts/backups/mindex_backup.sh >> /var/log/mycosoft/mindex_backup.log 2>&1
```

## Environment Variables

### backup_vms.sh
- `BACKUP_STORAGE` - Proxmox storage (default: local)
- `VM_IDS` - Comma-separated VM IDs (default: 187,188,189,190,191)
- `RETENTION_DAYS` - Days to keep (default: 7)

### mindex_backup.sh
- `MINDEX_BACKUP_DIR` - Output directory (default: /opt/mycosoft/backups/mindex)
- `MINDEX_BACKUP_RETENTION_HOURS` - Hours to keep (default: 24)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - Or use MINDEX_DB_* equivalents

## Restore Procedures

### MINDEX from pg_dump
```bash
gunzip -c /opt/mycosoft/backups/mindex/mindex_YYYYMMDD_HH.sql.gz | \
  psql -h localhost -U mycosoft -d mindex
```

### VM from vzdump
Use Proxmox UI: Datacenter → Backup → Restore, or `qmrestore` / `pct restore` CLI.
