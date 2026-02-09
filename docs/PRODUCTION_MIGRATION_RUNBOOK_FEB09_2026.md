# Production Migration Runbook

**Date**: February 9, 2026  
**Author**: MYCA Documentation Manager  
**Status**: Complete  

## Overview

This runbook covers all operational procedures for deploying, maintaining, rolling back, and recovering the Mycosoft production platform across its three VMs. Every command is copy-paste ready.

---

## 1. VM Deployment Plans

### 1.1 Website — VM 187 (Sandbox)

**IP**: 192.168.0.187  
**Service**: Next.js website in Docker  
**Port**: 3000  

```bash
# SSH into Sandbox VM
ssh mycosoft@192.168.0.187

# Pull latest code
cd /opt/mycosoft/website
git fetch origin
git reset --hard origin/main

# Build new Docker image
docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .

# Stop and remove old container
docker stop mycosoft-website
docker rm mycosoft-website

# Start new container (MUST include NAS volume mount)
docker run -d \
  --name mycosoft-website \
  -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped \
  mycosoft-always-on-mycosoft-website:latest

# Verify container is running
docker ps | grep mycosoft-website
docker logs --tail 50 mycosoft-website

# Purge Cloudflare cache (do this from Cloudflare dashboard or API)
# Dashboard: Cloudflare > mycosoft.com > Caching > Purge Everything
```

### 1.2 MAS Orchestrator — VM 188

**IP**: 192.168.0.188  
**Service**: FastAPI orchestrator (systemd)  
**Port**: 8001  

```bash
# SSH into MAS VM
ssh mycosoft@192.168.0.188

# Pull latest code
cd /home/mycosoft/mycosoft/mas
git fetch origin
git reset --hard origin/main

# Option A: Restart systemd service (preferred)
sudo systemctl restart mas-orchestrator
sudo systemctl status mas-orchestrator

# Option B: Docker rebuild (if using Docker)
docker build -t mycosoft/mas-agent:latest --no-cache .
docker stop myca-orchestrator-new
docker rm myca-orchestrator-new
docker run -d \
  --name myca-orchestrator-new \
  --restart unless-stopped \
  -p 8001:8000 \
  mycosoft/mas-agent:latest

# Verify
curl http://192.168.0.188:8001/health
docker logs --tail 50 myca-orchestrator-new
```

### 1.3 MINDEX — VM 189

**IP**: 192.168.0.189  
**Service**: MINDEX API + PostgreSQL + Redis + Qdrant  
**Ports**: 8000, 5432, 6379, 6333  

```bash
# SSH into MINDEX VM
ssh mycosoft@192.168.0.189

# Pull latest code
cd /home/mycosoft/mindex
git fetch origin
git reset --hard origin/main

# Restart MINDEX API only (preserves databases)
docker compose stop mindex-api
docker compose build --no-cache mindex-api
docker compose up -d mindex-api

# Restart all services (databases will preserve data in volumes)
docker compose down
docker compose up -d

# Verify
curl http://192.168.0.189:8000/health
docker compose ps
docker compose logs --tail 50 mindex-api
```

---

## 2. Docker Container Management

### Common Commands

```bash
# List all running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View container logs (last 100 lines, follow)
docker logs --tail 100 -f <container_name>

# Inspect container details
docker inspect <container_name>

# Enter container shell
docker exec -it <container_name> /bin/bash

# View resource usage
docker stats --no-stream

# Clean up unused images/containers
docker system prune -f
docker image prune -a -f  # WARNING: removes all unused images
```

### Image Tagging for Rollback

Before deploying a new version, tag the current image for rollback:

```bash
# Tag current image before rebuild
docker tag mycosoft-always-on-mycosoft-website:latest \
  mycosoft-always-on-mycosoft-website:backup-$(date +%Y%m%d-%H%M%S)

# List available image tags
docker images | grep mycosoft

# Rollback to tagged image
docker stop mycosoft-website
docker rm mycosoft-website
docker run -d \
  --name mycosoft-website \
  -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped \
  mycosoft-always-on-mycosoft-website:backup-20260209-143000
```

---

## 3. Rollback Procedures

### 3.1 Proxmox VM Snapshots

Proxmox manages all three VMs. Snapshots provide full VM-level rollback.

```bash
# Create snapshot before deployment (from Proxmox host or API)
# VM IDs: 187=website, 188=MAS, 189=MINDEX

# Via Proxmox CLI (on Proxmox host)
qm snapshot <VMID> pre-deploy-$(date +%Y%m%d) --description "Pre-deployment snapshot"

# Via Proxmox API
curl -k -X POST "https://<PROXMOX_HOST>:8006/api2/json/nodes/<NODE>/qemu/<VMID>/snapshot" \
  -H "Authorization: PVEAPIToken=<TOKEN>" \
  -d "snapname=pre-deploy-$(date +%Y%m%d)" \
  -d "description=Pre-deployment snapshot"

# Rollback to snapshot (CAUTION: stops VM)
qm rollback <VMID> pre-deploy-20260209

# List snapshots
qm listsnapshot <VMID>
```

**Schedule**: Create Proxmox snapshots before every deployment and retain for 7 days.

### 3.2 Docker Image Rollback

```bash
# On any VM: rollback to previous image tag
docker stop <container_name>
docker rm <container_name>
docker run -d --name <container_name> <previous_image_tag> [same flags as original]
```

### 3.3 Git Rollback

```bash
# Rollback to a specific commit
git log --oneline -10  # find the commit to rollback to
git reset --hard <commit_sha>

# Rollback to previous commit
git reset --hard HEAD~1

# Rollback and force push (CAUTION: rewrites history)
git push origin main --force

# Safer: revert a specific commit (creates new commit)
git revert <commit_sha>
git push origin main
```

---

## 4. Secrets Rotation Schedule and Procedure

### Rotation Schedule

| Secret Type | Rotation Frequency | Next Rotation | Owner |
|-------------|-------------------|---------------|-------|
| Supabase API Keys | Quarterly | April 2026 | CEO |
| Anthropic API Key | Quarterly | April 2026 | CEO |
| OpenAI API Key | Quarterly | April 2026 | CEO |
| Cloudflare API Token | Quarterly | April 2026 | CEO |
| Notion Integration Token | Quarterly | April 2026 | CEO |
| ElevenLabs API Key | Quarterly | April 2026 | CEO |
| n8n Webhook Secrets | Semi-annually | August 2026 | CEO |
| PostgreSQL Passwords | Semi-annually | August 2026 | CEO |
| SSH Keys | Annually | February 2027 | CEO |

### Rotation Procedure

```bash
# 1. Generate new secret/key from the provider's dashboard

# 2. Update .env on each affected VM
ssh mycosoft@<VM_IP>
nano /path/to/.env  # or use sed for specific key replacement

# 3. Update .env for Website (VM 187)
ssh mycosoft@192.168.0.187
cd /opt/mycosoft/website
nano .env.local  # Update the rotated key

# 4. Update .env for MAS (VM 188)
ssh mycosoft@192.168.0.188
cd /home/mycosoft/mycosoft/mas
nano .env  # Update the rotated key

# 5. Update .env for MINDEX (VM 189)
ssh mycosoft@192.168.0.189
cd /home/mycosoft/mindex
nano .env  # Update the rotated key

# 6. Restart affected services
# Website: rebuild container (see Section 1.1)
# MAS: sudo systemctl restart mas-orchestrator
# MINDEX: docker compose restart mindex-api

# 7. Verify all services are healthy (see Section 6)

# 8. Revoke old secret/key from the provider's dashboard

# 9. Update local dev .env files
# Website: C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local
# MAS: C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.env
```

**Important**: Never commit `.env` files to Git. Always update secrets on each VM individually.

---

## 5. Data Backup Steps

### 5.1 PostgreSQL (VM 189, port 5432)

```bash
# SSH to MINDEX VM
ssh mycosoft@192.168.0.189

# Full database dump
docker exec -t <postgres_container> pg_dump -U <user> -d <dbname> \
  -F c -f /tmp/backup_$(date +%Y%m%d).dump

# Copy dump out of container
docker cp <postgres_container>:/tmp/backup_$(date +%Y%m%d).dump \
  /opt/mycosoft/backups/postgres/

# Copy to NAS for offsite storage
cp /opt/mycosoft/backups/postgres/backup_$(date +%Y%m%d).dump \
  /mnt/nas/backups/postgres/

# Verify backup integrity
pg_restore --list /opt/mycosoft/backups/postgres/backup_$(date +%Y%m%d).dump

# Restore from backup (CAUTION: overwrites current data)
docker exec -t <postgres_container> pg_restore -U <user> -d <dbname> \
  -c /tmp/backup_$(date +%Y%m%d).dump
```

**Schedule**: Daily automated pg_dump at 02:00 UTC, retain 30 days.

### 5.2 Redis (VM 189, port 6379)

```bash
# Trigger RDB snapshot
docker exec <redis_container> redis-cli BGSAVE

# Copy RDB file
docker cp <redis_container>:/data/dump.rdb \
  /opt/mycosoft/backups/redis/dump_$(date +%Y%m%d).rdb

# Copy to NAS
cp /opt/mycosoft/backups/redis/dump_$(date +%Y%m%d).rdb \
  /mnt/nas/backups/redis/

# Restore from RDB (stop Redis first)
docker stop <redis_container>
docker cp /opt/mycosoft/backups/redis/dump_$(date +%Y%m%d).rdb \
  <redis_container>:/data/dump.rdb
docker start <redis_container>
```

**Schedule**: Daily RDB snapshot at 03:00 UTC, retain 14 days.

### 5.3 Qdrant (VM 189, port 6333)

```bash
# Create Qdrant snapshot via API
curl -X POST "http://192.168.0.189:6333/snapshots"

# List available snapshots
curl "http://192.168.0.189:6333/snapshots"

# Download snapshot
curl -o /opt/mycosoft/backups/qdrant/snapshot_$(date +%Y%m%d).snapshot \
  "http://192.168.0.189:6333/snapshots/<snapshot_name>"

# Copy to NAS
cp /opt/mycosoft/backups/qdrant/snapshot_$(date +%Y%m%d).snapshot \
  /mnt/nas/backups/qdrant/

# Restore from snapshot
curl -X PUT "http://192.168.0.189:6333/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{"location": "/opt/mycosoft/backups/qdrant/snapshot_$(date +%Y%m%d).snapshot"}'
```

**Schedule**: Weekly Qdrant snapshot on Sundays at 04:00 UTC, retain 8 weeks.

### 5.4 NAS Sync

```bash
# All backup directories are synced to NAS at \\192.168.0.105\mycosoft.com\backups\
# NAS mount point on VMs: /mnt/nas/backups/

# Verify NAS mount
df -h | grep nas
ls /mnt/nas/backups/

# Manual sync (if NAS mount is available)
rsync -av /opt/mycosoft/backups/ /mnt/nas/backups/
```

---

## 6. Health Check Commands

### Quick Health Check (All Services)

```bash
# Website (VM 187)
curl -s -o /dev/null -w "%{http_code}" http://192.168.0.187:3000

# MAS Orchestrator (VM 188)
curl -s http://192.168.0.188:8001/health

# MINDEX API (VM 189)
curl -s http://192.168.0.189:8000/health

# PostgreSQL (VM 189)
docker exec <postgres_container> pg_isready -U <user>

# Redis (VM 189)
docker exec <redis_container> redis-cli ping

# Qdrant (VM 189)
curl -s http://192.168.0.189:6333/healthz

# n8n (VM 188)
curl -s -o /dev/null -w "%{http_code}" http://192.168.0.188:5678

# Ollama (VM 188)
curl -s http://192.168.0.188:11434/api/tags
```

### Detailed Health Check Script

```bash
#!/bin/bash
# save as: check_all_services.sh

echo "=== Mycosoft Production Health Check ==="
echo "Date: $(date)"
echo ""

echo "--- VM 187 (Website) ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://192.168.0.187:3000)
echo "Website: $HTTP_CODE"

echo ""
echo "--- VM 188 (MAS) ---"
MAS=$(curl -s --connect-timeout 5 http://192.168.0.188:8001/health 2>/dev/null || echo "UNREACHABLE")
echo "MAS Orchestrator: $MAS"

N8N_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://192.168.0.188:5678)
echo "n8n: $N8N_CODE"

echo ""
echo "--- VM 189 (MINDEX) ---"
MINDEX=$(curl -s --connect-timeout 5 http://192.168.0.189:8000/health 2>/dev/null || echo "UNREACHABLE")
echo "MINDEX API: $MINDEX"

QDRANT=$(curl -s --connect-timeout 5 http://192.168.0.189:6333/healthz 2>/dev/null || echo "UNREACHABLE")
echo "Qdrant: $QDRANT"

echo ""
echo "=== Health Check Complete ==="
```

### Docker Container Health (per VM)

```bash
# On any VM
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## 7. Emergency Recovery Procedures

### 7.1 Service Unresponsive

```bash
# 1. Check if container is running
docker ps | grep <container_name>

# 2. Check container logs for errors
docker logs --tail 200 <container_name>

# 3. Restart the container
docker restart <container_name>

# 4. If restart fails, recreate
docker stop <container_name>
docker rm <container_name>
# Re-run docker run command from Section 1

# 5. If container won't start, check disk space
df -h
docker system df

# 6. If out of disk, clean up
docker system prune -f
docker image prune -a -f  # removes unused images
```

### 7.2 VM Unresponsive

```bash
# 1. Try SSH
ssh mycosoft@192.168.0.<IP> -o ConnectTimeout=10

# 2. If SSH fails, restart VM from Proxmox
# Via Proxmox Web UI: Datacenter > Node > VM > Shutdown/Start
# Via CLI on Proxmox host:
qm stop <VMID>
sleep 10
qm start <VMID>

# 3. If VM won't start, rollback to last snapshot
qm rollback <VMID> <snapshot_name>
qm start <VMID>

# 4. After VM restarts, verify services auto-started
docker ps
systemctl status mas-orchestrator  # on VM 188
```

### 7.3 Database Corruption

```bash
# 1. Stop all services writing to the database
docker compose stop mindex-api

# 2. Check PostgreSQL logs
docker logs <postgres_container> --tail 200

# 3. Run consistency check
docker exec <postgres_container> psql -U <user> -d <dbname> -c "SELECT count(*) FROM pg_stat_activity;"

# 4. If corruption confirmed, restore from backup
docker compose stop  # stop everything
docker exec <postgres_container> pg_restore -U <user> -d <dbname> -c /tmp/latest_backup.dump
docker compose up -d

# 5. If backup restore fails, rollback entire VM
qm rollback <VMID_189> <last_good_snapshot>
qm start <VMID_189>
```

### 7.4 Complete Platform Recovery

In the worst case (all VMs down), recover in this order:

1. **MINDEX (VM 189)** — Start databases first (PostgreSQL, Redis, Qdrant)
2. **MAS (VM 188)** — Start orchestrator (depends on MINDEX for data)
3. **Website (VM 187)** — Start website last (depends on MAS and MINDEX)

```bash
# Step 1: Recover MINDEX
qm start <VMID_189>
# Wait for VM to boot, then verify
ssh mycosoft@192.168.0.189 "docker compose up -d && docker compose ps"

# Step 2: Recover MAS
qm start <VMID_188>
ssh mycosoft@192.168.0.188 "sudo systemctl start mas-orchestrator"
curl http://192.168.0.188:8001/health

# Step 3: Recover Website
qm start <VMID_187>
ssh mycosoft@192.168.0.187 "docker start mycosoft-website"
curl http://192.168.0.187:3000

# Step 4: Verify end-to-end
curl https://mycosoft.com
```

### 7.5 Emergency Contacts and Escalation

| Priority | Situation | Action |
|----------|-----------|--------|
| P1 | All services down | Full platform recovery (Section 7.4) |
| P2 | Database corruption | Restore from backup (Section 7.3) |
| P3 | Single VM down | VM recovery (Section 7.2) |
| P4 | Single service down | Service restart (Section 7.1) |
| P5 | Performance degradation | Check resource usage, scale if needed |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `docs/MASTER_ARCHITECTURE_FEB09_2026.md` | System architecture and diagrams |
| `docs/SYSTEM_REGISTRY_FEB04_2026.md` | Complete system registry |
| `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` | VM layout details |
| `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md` | Dev-to-sandbox pipeline |
| `docs/MAS_ORCHESTRATOR_SERVICE_FEB06_2026.md` | MAS orchestrator service details |
| `docs/MINDEX_VM_DEPLOYMENT_STATUS_FEB04_2026.md` | MINDEX deployment status |
