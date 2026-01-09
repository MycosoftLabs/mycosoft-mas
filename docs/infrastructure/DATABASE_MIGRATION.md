# Database Migration to NAS Storage

This document describes migrating PostgreSQL, Redis, and Qdrant from local Docker volumes to the UDM Pro 26TB NAS storage.

## Overview

| Database | Current Location | New Location |
|----------|------------------|--------------|
| PostgreSQL | Docker volume | /mnt/mycosoft/databases/postgres |
| Redis | Docker volume | /mnt/mycosoft/databases/redis |
| Qdrant | Docker volume | /mnt/mycosoft/knowledge/qdrant |

## Prerequisites

1. NAS mounted on all nodes at `/mnt/mycosoft`
2. Docker containers stopped
3. Backup of existing data

## Step 1: Verify NAS Mount

```bash
# Check if NAS is mounted
mountpoint -q /mnt/mycosoft && echo "NAS is mounted" || echo "NAS NOT mounted"

# Check available space
df -h /mnt/mycosoft
```

## Step 2: Run Migration Script

```bash
# On MYCA Core VM
sudo chmod +x scripts/migrate_databases_to_nas.sh
sudo ./scripts/migrate_databases_to_nas.sh
```

This script will:
- Create directory structure on NAS
- Stop running containers
- Backup existing data
- Set proper permissions

## Step 3: Update Docker Compose

The production docker-compose configuration should use NAS volumes:

```yaml
services:
  postgres:
    image: postgres:17-alpine
    volumes:
      - /mnt/mycosoft/databases/postgres:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: mas
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: mas

  redis:
    image: redis:8-alpine
    volumes:
      - /mnt/mycosoft/databases/redis:/data
    command: redis-server --appendonly yes

  qdrant:
    image: qdrant/qdrant:v1.13.2
    volumes:
      - /mnt/mycosoft/knowledge/qdrant:/qdrant/storage
```

## Step 4: Start Services

```bash
# Start with new volume mounts
docker compose up -d postgres redis qdrant

# Verify services are healthy
docker compose ps
docker compose logs postgres
```

## Step 5: Verify Data Integrity

```bash
# Check PostgreSQL
docker exec mas-postgres psql -U mas -c "\dt"

# Check Redis
docker exec mas-redis redis-cli ping

# Check Qdrant
curl http://localhost:6333/collections
```

## Rollback Procedure

If migration fails:

```bash
# Stop containers
docker compose down

# Restore from backup
sudo cp -r /mnt/mycosoft/backups/migration_*/postgres/* \
    /var/lib/docker/volumes/mycosoft-mas_postgres_data/_data/

# Revert docker-compose to use local volumes
# Then restart
docker compose up -d
```

## NFS Performance Tuning

For better database performance on NFS:

1. Use NFS v4 with proper options:
   ```
   192.168.0.1:/mycosoft /mnt/mycosoft nfs4 rw,hard,intr,rsize=65536,wsize=65536 0 0
   ```

2. Consider local SSD cache for frequently accessed data

3. Monitor I/O latency:
   ```bash
   iostat -x 1
   ```

## Backup Strategy

With data on NAS, implement regular backups:

### PostgreSQL Backups

```bash
# Daily backup
docker exec mas-postgres pg_dumpall -U mas > /mnt/mycosoft/backups/daily/postgres_$(date +%Y%m%d).sql

# Compressed backup
docker exec mas-postgres pg_dumpall -U mas | gzip > /mnt/mycosoft/backups/daily/postgres_$(date +%Y%m%d).sql.gz
```

### Qdrant Snapshots

```bash
# Create snapshot
curl -X POST "http://localhost:6333/snapshots"

# List snapshots
curl "http://localhost:6333/snapshots"
```

### Automated Backups

Add to crontab:

```cron
# Daily PostgreSQL backup at 2 AM
0 2 * * * /opt/myca/scripts/backup_postgres.sh

# Weekly Qdrant snapshot at 3 AM Sunday
0 3 * * 0 /opt/myca/scripts/backup_qdrant.sh
```

## Monitoring

Monitor NAS storage usage:

```bash
# Check usage
du -sh /mnt/mycosoft/databases/*
du -sh /mnt/mycosoft/knowledge/*

# Check NFS status
nfsstat -c
```
