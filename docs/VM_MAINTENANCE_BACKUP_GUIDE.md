# VM Maintenance & Backup Guide

*Created: January 17, 2026*  
*For: VM 103 (mycosoft-sandbox) & VM 104 (mycosoft-prod)*

---

## 📋 Table of Contents

1. [Daily Maintenance](#1-daily-maintenance)
2. [Weekly Maintenance](#2-weekly-maintenance)
3. [Backup Strategies](#3-backup-strategies)
4. [Disaster Recovery](#4-disaster-recovery)
5. [Monitoring & Alerts](#5-monitoring--alerts)
6. [Scaling Guidelines](#6-scaling-guidelines)
7. [Production Deployment](#7-production-deployment)

---

## 1. Daily Maintenance

### Automated Health Check (Cron)

```bash
# Add to crontab
crontab -e

# Add these lines:
# Health check every 5 minutes
*/5 * * * * /opt/mycosoft/scripts/health-check.sh >> /opt/mycosoft/logs/health-check.log 2>&1

# Log rotation daily
0 0 * * * /usr/sbin/logrotate /opt/mycosoft/scripts/logrotate.conf
```

### Log Rotation Configuration

```bash
cat > /opt/mycosoft/scripts/logrotate.conf << 'EOF'
/opt/mycosoft/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 640 mycosoft mycosoft
}
EOF
```

### Daily Checklist

| Task | Command | Frequency |
|------|---------|-----------|
| Check container status | `docker ps` | Every 4 hours |
| Check disk space | `df -h` | Daily |
| Check memory | `free -h` | Daily |
| Review logs | `docker compose logs --tail=100` | Daily |
| Check Cloudflare tunnel | `sudo systemctl status cloudflared` | Daily |

---

## 2. Weekly Maintenance

### System Updates

```bash
# Create update script
cat > /opt/mycosoft/scripts/weekly-update.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Weekly System Update $(date) ==="

# Update system packages
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y

# Update Docker images
cd /opt/mycosoft/mas
docker compose pull
docker compose -f docker-compose.always-on.yml pull

cd /opt/mycosoft/website
docker compose pull

# Prune old images
docker image prune -f

# Clean up unused volumes (be careful!)
# docker volume prune -f

echo "Update complete!"
EOF

chmod +x /opt/mycosoft/scripts/weekly-update.sh
```

### Database Maintenance

```bash
# PostgreSQL vacuum and analyze
docker exec mycosoft-postgres psql -U mycosoft -d mycosoft_mas -c "VACUUM ANALYZE;"
docker exec mycosoft-postgres psql -U mycosoft -d mindex -c "VACUUM ANALYZE;"
docker exec mycosoft-postgres psql -U mycosoft -d website -c "VACUUM ANALYZE;"

# Check database size
docker exec mycosoft-postgres psql -U mycosoft -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) AS size FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC;"
```

### Docker Cleanup

```bash
# Create cleanup script
cat > /opt/mycosoft/scripts/docker-cleanup.sh << 'EOF'
#!/bin/bash

echo "=== Docker Cleanup $(date) ==="

# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -f

# Remove unused networks
docker network prune -f

# Show disk usage
docker system df

echo "Cleanup complete!"
EOF

chmod +x /opt/mycosoft/scripts/docker-cleanup.sh
```

---

## 3. Backup Strategies

### 3.1 Database Backups

```bash
# Create backup directory
mkdir -p /opt/mycosoft/backups/postgres

# Database backup script
cat > /opt/mycosoft/scripts/backup-database.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/mycosoft/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

echo "=== Database Backup $(date) ==="

# Backup all databases
for db in mycosoft_mas mindex website n8n; do
    echo "Backing up $db..."
    docker exec mycosoft-postgres pg_dump -U mycosoft -d $db | gzip > "$BACKUP_DIR/${db}_${DATE}.sql.gz"
done

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# List backups
echo "Current backups:"
ls -lh $BACKUP_DIR

echo "Backup complete!"
EOF

chmod +x /opt/mycosoft/scripts/backup-database.sh
```

### 3.2 Volume Backups

```bash
# Backup Docker volumes
cat > /opt/mycosoft/scripts/backup-volumes.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/mycosoft/backups/volumes"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "=== Volume Backup $(date) ==="

# n8n data
docker run --rm \
    -v mycosoft-mas_n8n_data:/data \
    -v $BACKUP_DIR:/backup \
    alpine tar czf /backup/n8n_data_${DATE}.tar.gz -C /data .

# Grafana data
docker run --rm \
    -v mycosoft-always-on_grafana_data:/data \
    -v $BACKUP_DIR:/backup \
    alpine tar czf /backup/grafana_data_${DATE}.tar.gz -C /data .

# Redis data
docker run --rm \
    -v mycosoft-mas_redis_data:/data \
    -v $BACKUP_DIR:/backup \
    alpine tar czf /backup/redis_data_${DATE}.tar.gz -C /data .

# Cleanup old backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Volume backup complete!"
EOF

chmod +x /opt/mycosoft/scripts/backup-volumes.sh
```

### 3.3 Full VM Snapshot (Proxmox)

Using Proxmox API or CLI:

```bash
# From Proxmox host or via API
# Create snapshot
pvesh create /nodes/pve/qemu/103/snapshot --snapname backup_$(date +%Y%m%d) --description "Automated backup"

# List snapshots
pvesh get /nodes/pve/qemu/103/snapshot

# Rollback (if needed)
pvesh post /nodes/pve/qemu/103/snapshot/backup_YYYYMMDD/rollback
```

### 3.4 Offsite Backup (to NAS)

```bash
# Sync backups to NAS
cat > /opt/mycosoft/scripts/sync-to-nas.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Syncing backups to NAS $(date) ==="

# Sync to NAS (adjust path as needed)
rsync -avz --delete /opt/mycosoft/backups/ /mnt/nas/mycosoft/backups/

echo "Sync complete!"
EOF

chmod +x /opt/mycosoft/scripts/sync-to-nas.sh
```

### Backup Schedule (Cron)

```bash
# Add to crontab
crontab -e

# Database backup - daily at 2 AM
0 2 * * * /opt/mycosoft/scripts/backup-database.sh >> /opt/mycosoft/logs/backup.log 2>&1

# Volume backup - daily at 3 AM
0 3 * * * /opt/mycosoft/scripts/backup-volumes.sh >> /opt/mycosoft/logs/backup.log 2>&1

# Sync to NAS - daily at 4 AM
0 4 * * * /opt/mycosoft/scripts/sync-to-nas.sh >> /opt/mycosoft/logs/backup.log 2>&1

# VM snapshot - weekly on Sunday at 1 AM (run from Proxmox)
```

---

## 4. Disaster Recovery

### Recovery Procedures

#### 4.1 Restore Database

```bash
# Stop affected services
docker compose down

# Restore from backup
gunzip -c /opt/mycosoft/backups/postgres/mycosoft_mas_YYYYMMDD_HHMMSS.sql.gz | \
    docker exec -i mycosoft-postgres psql -U mycosoft -d mycosoft_mas

# Restart services
docker compose up -d
```

#### 4.2 Restore Volumes

```bash
# Stop services
docker compose down

# Restore n8n data
docker run --rm \
    -v mycosoft-mas_n8n_data:/data \
    -v /opt/mycosoft/backups/volumes:/backup \
    alpine tar xzf /backup/n8n_data_YYYYMMDD_HHMMSS.tar.gz -C /data

# Start services
docker compose up -d
```

#### 4.3 Full VM Restore

From Proxmox:
1. Stop the VM
2. Rollback to snapshot or restore from backup
3. Start the VM
4. Verify all services

### Recovery Checklist

| Step | Action | Verify |
|------|--------|--------|
| 1 | Stop all services | `docker ps` shows no containers |
| 2 | Restore database | No errors during restore |
| 3 | Restore volumes | Files present in volumes |
| 4 | Start services | All containers running |
| 5 | Health check | All endpoints respond |
| 6 | Test functionality | Manual testing |

---

## 5. Monitoring & Alerts

### Prometheus Alerting Rules

```yaml
# /opt/mycosoft/monitoring/alert-rules.yml
groups:
  - name: mycosoft-alerts
    rules:
      - alert: ContainerDown
        expr: absent(container_last_seen{name=~"mycosoft.*"})
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.name }} is down"
      
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Memory usage above 90%"
      
      - alert: HighDiskUsage
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Disk usage above 85%"
```

### Simple Email Alert Script

```bash
cat > /opt/mycosoft/scripts/alert.sh << 'EOF'
#!/bin/bash

SUBJECT="$1"
MESSAGE="$2"
EMAIL="admin@mycosoft.com"

# Using mailutils or similar
echo "$MESSAGE" | mail -s "ALERT: $SUBJECT" $EMAIL

# Or use a webhook (n8n, Slack, Discord)
curl -X POST "https://n8n.mycosoft.com/webhook/alert" \
    -H "Content-Type: application/json" \
    -d "{\"subject\": \"$SUBJECT\", \"message\": \"$MESSAGE\"}"
EOF

chmod +x /opt/mycosoft/scripts/alert.sh
```

---

## 6. Scaling Guidelines

### When to Scale

| Metric | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| CPU | > 70% sustained | > 90% sustained |
| Memory | > 80% used | > 95% used |
| Disk | > 70% used | > 90% used |
| Response Time | > 2 seconds | > 5 seconds |

### Vertical Scaling (Increase Resources)

From Proxmox:
```bash
# Stop VM
qm stop 103

# Increase memory
qm set 103 --memory 65536  # 64GB

# Increase CPU
qm set 103 --cores 16

# Start VM
qm start 103
```

### Horizontal Scaling (Add More VMs)

For high availability:
1. Clone VM 103 to create additional nodes
2. Set up load balancer (Cloudflare Load Balancing)
3. Configure shared database or replication
4. Update Cloudflare tunnel to include multiple origins

---

## 7. Production Deployment

### Sandbox to Production Checklist

| Step | Task | Status |
|------|------|--------|
| 1 | All tests passing on sandbox | ☐ |
| 2 | All services healthy | ☐ |
| 3 | Backup sandbox VM | ☐ |
| 4 | Create production VM (ID 104) | ☐ |
| 5 | Clone sandbox to production | ☐ |
| 6 | Update production environment variables | ☐ |
| 7 | Update Cloudflare DNS | ☐ |
| 8 | Test production endpoints | ☐ |
| 9 | Configure monitoring for production | ☐ |
| 10 | Document any differences | ☐ |

### Clone Sandbox to Production

From Proxmox:
```bash
# Full clone (not linked)
qm clone 103 104 --name mycosoft-prod --full true

# Update production VM settings
qm set 104 --onboot 1  # Start at boot
qm set 104 --memory 65536  # 64GB for production
qm set 104 --cores 16  # 16 cores for production
```

### Production Environment Differences

| Setting | Sandbox | Production |
|---------|---------|------------|
| VM ID | 103 | 104 |
| VM Name | mycosoft-sandbox | mycosoft-prod |
| Start at boot | No | Yes |
| Memory | 32 GB | 64 GB |
| CPU Cores | 8 | 16 |
| Disk | 256 GB | 500 GB |
| Cloudflare | test.mycosoft.com | mycosoft.com |
| NODE_ENV | development | production |
| Log Level | debug | info |

---

## 📊 Quick Reference Commands

```bash
# Start all services
/opt/mycosoft/scripts/start-all.sh

# Stop all services
/opt/mycosoft/scripts/stop-all.sh

# Health check
/opt/mycosoft/scripts/health-check.sh

# Backup database
/opt/mycosoft/scripts/backup-database.sh

# View logs
docker compose logs -f --tail=100

# Restart specific service
docker compose restart <service_name>

# Check disk space
df -h && docker system df

# Check memory
free -h

# Check CPU
htop
```

---

*Document Version: 1.0*  
*Last Updated: January 17, 2026*
