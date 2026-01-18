# Mycosoft Production Runbook

## Overview

This runbook provides operational procedures for the Mycosoft MAS production environment running on Proxmox VMs.

## System Architecture

- **VM1 (Production)**: All services, containers, databases
- **VM2 (Code Operator)**: Development tools, AI assistants
- **NAS**: Persistent storage for databases and backups
- **Cloudflare Tunnel**: Secure external access
- **UniFi Dream Machine**: Network gateway

## Service Startup Procedures

### Normal Startup

```bash
# SSH to VM1
ssh mycosoft@192.168.1.100

# Navigate to workspace
cd /opt/mycosoft

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Verify services
./migration/health-check.sh
```

### Startup Order (if needed)

```bash
# 1. Infrastructure
docker-compose -f docker-compose.prod.yml up -d postgres redis qdrant

# 2. Wait for infrastructure
sleep 15

# 3. Core services
docker-compose -f docker-compose.prod.yml up -d mas-orchestrator

# 4. Application services
docker-compose -f docker-compose.prod.yml up -d website mycobrain-service

# 5. Supporting services
docker-compose -f docker-compose.prod.yml up -d prometheus grafana n8n
```

## Service Management

### View Service Status

```bash
docker-compose -f docker-compose.prod.yml ps
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f mas-orchestrator
```

### Restart Service

```bash
docker-compose -f docker-compose.prod.yml restart [service-name]
```

### Stop Service

```bash
docker-compose -f docker-compose.prod.yml stop [service-name]
```

### Update Service

```bash
# Pull latest code
cd /opt/mycosoft
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build [service-name]
```

## Backup Procedures

### Daily Automated Backups

Backups run automatically at 2 AM daily via cron job.

### Manual Backup

```bash
# On Proxmox server
./migration/daily-backup.sh
```

### Database Backup

```bash
# PostgreSQL
docker exec mycosoft-postgres pg_dump -U mas mas > /mnt/mycosoft-nas/backups/postgres_$(date +%Y%m%d).sql

# Redis
docker exec mycosoft-redis redis-cli SAVE
docker cp mycosoft-redis:/data/dump.rdb /mnt/mycosoft-nas/backups/redis_$(date +%Y%m%d).rdb
```

## Restore Procedures

### VM Restore from Backup

1. **Stop VM in Proxmox:**
   ```bash
   qm stop 100
   ```

2. **Restore from backup:**
   - Proxmox Web UI → VM 100 → Backup → Restore
   - Select latest backup
   - Restore

3. **Start VM:**
   ```bash
   qm start 100
   ```

4. **Verify services:**
   ```bash
   ssh mycosoft@192.168.1.100
   ./migration/health-check.sh
   ```

### Database Restore

```bash
# PostgreSQL
docker exec -i mycosoft-postgres psql -U mas -d mas < /mnt/mycosoft-nas/backups/postgres_YYYYMMDD.sql

# Redis
docker cp /mnt/mycosoft-nas/backups/redis_YYYYMMDD.rdb mycosoft-redis:/data/dump.rdb
docker restart mycosoft-redis
```

## Troubleshooting

### Service Not Starting

1. **Check logs:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs [service-name]
   ```

2. **Check container status:**
   ```bash
   docker ps -a | grep [service-name]
   ```

3. **Check dependencies:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

4. **Restart service:**
   ```bash
   docker-compose -f docker-compose.prod.yml restart [service-name]
   ```

### Database Connection Issues

```bash
# Test PostgreSQL
docker exec mycosoft-postgres psql -U mas -d mas -c "SELECT version();"

# Test Redis
docker exec mycosoft-redis redis-cli PING

# Check network
docker network inspect mycosoft-mas_mycosoft-net
```

### Cloudflare Tunnel Issues

```bash
# Check status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f

# Restart tunnel
sudo systemctl restart cloudflared
```

### NAS Mount Issues

```bash
# Check mount
mountpoint /mnt/mycosoft-nas

# Remount
sudo mount -a

# Check fstab
cat /etc/fstab | grep mycosoft-nas
```

### High Resource Usage

```bash
# Check memory
free -h

# Check disk
df -h

# Check container resources
docker stats
```

## Monitoring

### Health Checks

```bash
# Run health check script
./migration/health-check.sh

# Check specific service
curl http://localhost:8001/health
```

### Access Dashboards

- **Grafana**: http://192.168.1.100:3002 (admin/[password])
- **Prometheus**: http://192.168.1.100:9090
- **n8n**: http://192.168.1.100:5678

### Log Monitoring

```bash
# Follow all logs
docker-compose -f docker-compose.prod.yml logs -f

# Follow specific service
docker-compose -f docker-compose.prod.yml logs -f mas-orchestrator
```

## Emergency Procedures

### Complete System Failure

1. **Stop all services:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Restore from VM backup** (see Restore Procedures)

3. **Or restore from database backups:**
   ```bash
   # Restore databases
   # Then restart services
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Service Outage

1. **Identify affected service**
2. **Check logs for errors**
3. **Restart service**
4. **If persistent, restore from backup**

### Security Incident

1. **Immediately stop affected services**
2. **Review logs for suspicious activity**
3. **Change all passwords**
4. **Update firewall rules if needed**
5. **Notify security team**

## Maintenance Windows

### Scheduled Maintenance

- **Time**: 2 AM - 4 AM (when backups run)
- **Frequency**: Weekly or as needed
- **Procedures**:
  1. Notify users
  2. Stop non-critical services
  3. Perform updates
  4. Run health checks
  5. Restart services

### Update Procedures

```bash
# 1. Backup current state
./migration/daily-backup.sh

# 2. Pull latest code
cd /opt/mycosoft
git pull

# 3. Update containers
docker-compose -f docker-compose.prod.yml pull

# 4. Rebuild if needed
docker-compose -f docker-compose.prod.yml build

# 5. Restart services
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify
./migration/health-check.sh
```

## Contact Information

- **System Administrator**: [Your contact]
- **Emergency Contact**: [Emergency contact]
- **Proxmox Server**: [Server IP/URL]
- **Documentation**: /opt/mycosoft/docs/

## Service URLs

### Internal (VM1)
- Website: http://192.168.1.100:3000
- MAS API: http://192.168.1.100:8001
- MycoBrain: http://192.168.1.100:8003
- Grafana: http://192.168.1.100:3002
- Prometheus: http://192.168.1.100:9090
- n8n: http://192.168.1.100:5678

### External (via Cloudflare)
- Website: https://mycosoft.com
- API: https://api.mycosoft.com
