# Migration Checklist

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **Purpose**: Migrate MYCA from mycocomp (development) to Proxmox production cluster

This document provides a step-by-step checklist for migrating the MYCA system from the development workstation (mycocomp) to the production Proxmox cluster in the garage server network.

---

## Table of Contents

1. [Migration Overview](#migration-overview)
2. [Pre-Migration Verification](#pre-migration-verification)
3. [Phase 1: Data Backup](#phase-1-data-backup)
4. [Phase 2: Database Migration](#phase-2-database-migration)
5. [Phase 3: Docker Image Transfer](#phase-3-docker-image-transfer)
6. [Phase 4: Configuration Updates](#phase-4-configuration-updates)
7. [Phase 5: Service Deployment](#phase-5-service-deployment)
8. [Phase 6: DNS Cutover](#phase-6-dns-cutover)
9. [Post-Migration Verification](#post-migration-verification)
10. [Rollback Plan](#rollback-plan)
11. [Troubleshooting](#troubleshooting)

---

## Migration Overview

### Source and Target

| Aspect | Source (Dev) | Target (Prod) |
|--------|--------------|---------------|
| **Location** | mycocomp | Proxmox Cluster |
| **IP Range** | 192.168.0.x | 192.168.20.x |
| **Storage** | M:\ (NAS mapped) | /mnt/mycosoft (NFS) |
| **Environment** | development.env | production.env |
| **GPU** | RTX 5090 (local) | CPU only (or passthrough) |

### Migration Timeline

```
Day 1: Preparation and Backup
├── Pre-migration checks
├── Full data backup
└── Verify backup integrity

Day 2: Database and Data Migration
├── Stop development services
├── Export databases
├── Transfer to NAS
└── Import to production

Day 3: Service Deployment
├── Deploy Docker containers
├── Configure services
├── Initial testing
└── Smoke tests

Day 4: Cutover
├── DNS changes
├── Cloudflare tunnel update
├── Full testing
└── Monitor

Day 5+: Stabilization
├── Monitor production
├── Fix issues
├── Document lessons learned
```

---

## Pre-Migration Verification

### Infrastructure Readiness

- [ ] **Proxmox cluster operational**
  ```bash
  # SSH to Build node
  ssh root@192.168.0.202
  pvecm status
  ```

- [ ] **VMs created and accessible**
  ```bash
  # List all VMs
  qm list
  
  # Verify MYCA Core VM
  qm status 100
  ```

- [ ] **NAS storage mounted on all nodes**
  ```bash
  # Check NFS mount
  df -h | grep mycosoft
  ls -la /mnt/mycosoft
  ```

- [ ] **Network connectivity verified**
  ```bash
  # From myca-core VM
  ping 192.168.0.1  # UDM Pro
  ping 192.168.0.202  # Build node
  ```

### Development Environment Status

- [ ] **Current state documented**
  ```powershell
  # On mycocomp
  docker ps > pre_migration_containers.txt
  docker images > pre_migration_images.txt
  ```

- [ ] **All code committed to git**
  ```bash
  git status  # Should show clean working tree
  git log -1  # Document last commit
  ```

- [ ] **Environment variables documented**
  ```powershell
  # Export current environment
  Get-ChildItem Env: | Where-Object { $_.Name -like "*MYCA*" -or $_.Name -like "*NAS*" } > env_vars.txt
  ```

### Checklist Sign-off

| Item | Status | Verified By | Date |
|------|--------|-------------|------|
| Proxmox cluster ready | [ ] | | |
| VMs created | [ ] | | |
| NAS accessible from VMs | [ ] | | |
| Code repository clean | [ ] | | |
| Backup storage available | [ ] | | |

---

## Phase 1: Data Backup

### Step 1.1: Database Backup

**PostgreSQL:**

```powershell
# On mycocomp
docker exec mas-postgres pg_dumpall -U mas > M:\backups\migration\postgres_full_$(Get-Date -Format "yyyyMMdd").sql
```

**Redis:**

```powershell
# Trigger Redis BGSAVE
docker exec mas-redis redis-cli BGSAVE

# Copy dump file
Copy-Item \\wsl$\docker-desktop-data\data\docker\volumes\mas_redis-data\_data\dump.rdb M:\backups\migration\
```

**Qdrant:**

```powershell
# Create Qdrant snapshot
Invoke-RestMethod -Uri "http://localhost:6345/collections" | ForEach-Object {
    $collection = $_.result.collections.name
    Invoke-RestMethod -Method POST -Uri "http://localhost:6345/collections/$collection/snapshots"
}

# Copy snapshots
Copy-Item -Recurse \\wsl$\docker-desktop-data\data\docker\volumes\mas_qdrant-data\_data\snapshots M:\backups\migration\
```

### Step 1.2: Configuration Backup

```powershell
# Backup all configuration files
Copy-Item -Recurse config M:\backups\migration\config

# Backup environment files
Copy-Item .env* M:\backups\migration\

# Backup docker-compose files
Copy-Item docker-compose*.yml M:\backups\migration\
```

### Step 1.3: Application Data Backup

```powershell
# Agent data
Copy-Item -Recurse M:\agents\* M:\backups\migration\agents\

# Knowledge base
Copy-Item -Recurse M:\knowledge\* M:\backups\migration\knowledge\

# Website assets
Copy-Item -Recurse M:\website\* M:\backups\migration\website\
```

### Step 1.4: Verify Backup Integrity

```powershell
# Check backup sizes
Get-ChildItem M:\backups\migration -Recurse | Measure-Object -Property Length -Sum

# Generate checksums
Get-ChildItem M:\backups\migration -File | ForEach-Object {
    Get-FileHash $_.FullName -Algorithm SHA256
} > M:\backups\migration\checksums.txt
```

### Backup Checklist

| Backup | Location | Size | Checksum Verified |
|--------|----------|------|-------------------|
| PostgreSQL dump | M:\backups\migration\ | [ ] | [ ] |
| Redis dump | M:\backups\migration\ | [ ] | [ ] |
| Qdrant snapshots | M:\backups\migration\ | [ ] | [ ] |
| Configuration | M:\backups\migration\config\ | [ ] | [ ] |
| Agent data | M:\backups\migration\agents\ | [ ] | [ ] |
| Knowledge base | M:\backups\migration\knowledge\ | [ ] | [ ] |

---

## Phase 2: Database Migration

### Step 2.1: Stop Development Services

```powershell
# Stop all containers on mycocomp
docker compose down

# Verify stopped
docker ps  # Should be empty
```

### Step 2.2: Prepare Production Database

```bash
# SSH to myca-database VM
ssh myca@192.168.20.12

# Start database containers
docker compose -f docker-compose.db.yml up -d

# Verify running
docker ps
```

### Step 2.3: Import PostgreSQL

```bash
# Copy backup from NAS
cp /mnt/mycosoft/backups/migration/postgres_full_*.sql /tmp/

# Import into production PostgreSQL
docker exec -i myca-postgres psql -U mas < /tmp/postgres_full_*.sql

# Verify import
docker exec myca-postgres psql -U mas -c "\dt"
docker exec myca-postgres psql -U mas -c "SELECT COUNT(*) FROM agents;"
```

### Step 2.4: Import Redis

```bash
# Stop Redis to import
docker stop myca-redis

# Copy dump file
cp /mnt/mycosoft/backups/migration/dump.rdb /mnt/mycosoft/databases/redis/

# Start Redis
docker start myca-redis

# Verify keys
docker exec myca-redis redis-cli KEYS "*" | head
```

### Step 2.5: Import Qdrant

```bash
# Copy snapshots
cp -r /mnt/mycosoft/backups/migration/snapshots/* /mnt/mycosoft/knowledge/qdrant/snapshots/

# Restore each collection
curl -X POST "http://localhost:6333/collections/agents/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{"location": "/qdrant/snapshots/agents/<snapshot-name>"}'

# Verify collections
curl http://localhost:6333/collections
```

### Database Migration Checklist

| Database | Imported | Verified | Record Count |
|----------|----------|----------|--------------|
| PostgreSQL | [ ] | [ ] | |
| Redis | [ ] | [ ] | |
| Qdrant | [ ] | [ ] | |

---

## Phase 3: Docker Image Transfer

### Step 3.1: Build Production Images

```powershell
# On mycocomp, build and save images
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

# Build production images
docker compose -f docker-compose.yml build

# Save images to tar files
docker save mycosoft/mas-api:latest | gzip > M:\backups\migration\images\mas-api.tar.gz
docker save mycosoft/mas-website:latest | gzip > M:\backups\migration\images\mas-website.tar.gz
docker save mycosoft/mas-n8n:latest | gzip > M:\backups\migration\images\mas-n8n.tar.gz
```

### Step 3.2: Transfer to Production

```bash
# On myca-core VM
# Images are already on NAS

# Load images
gunzip -c /mnt/mycosoft/backups/migration/images/mas-api.tar.gz | docker load
gunzip -c /mnt/mycosoft/backups/migration/images/mas-website.tar.gz | docker load
gunzip -c /mnt/mycosoft/backups/migration/images/mas-n8n.tar.gz | docker load

# Verify images
docker images | grep mycosoft
```

### Alternative: Build on Production

```bash
# Clone repository on production
git clone https://github.com/mycosoft/mycosoft-mas.git /opt/myca
cd /opt/myca

# Build directly on production
docker compose build
```

### Image Transfer Checklist

| Image | Transferred | Loaded | Tag |
|-------|-------------|--------|-----|
| mas-api | [ ] | [ ] | |
| mas-website | [ ] | [ ] | |
| mas-n8n | [ ] | [ ] | |
| mas-dashboard | [ ] | [ ] | |

---

## Phase 4: Configuration Updates

### Step 4.1: Update Environment Variables

```bash
# On myca-core VM
cd /opt/myca

# Copy production environment
cp config/production.env .env

# Review and update
nano .env
```

**Key changes for production:**

```bash
# Environment
MAS_ENV=production
DEBUG_MODE=false

# Database URLs (now local to VM)
DATABASE_URL=postgresql://mas:${POSTGRES_PASSWORD}@192.168.20.12:5432/mas
REDIS_URL=redis://192.168.20.12:6379
QDRANT_URL=http://192.168.20.12:6333

# NAS paths (NFS mount)
NAS_STORAGE_PATH=/mnt/mycosoft

# Website URL
WEBSITE_URL=https://mycosoft.com

# CORS origins
CORS_ORIGINS=https://mycosoft.com,https://www.mycosoft.com
```

### Step 4.2: Update Cloudflare Tunnel

```bash
# Update tunnel config to point to production IPs
sudo nano /etc/cloudflared/config.yml

# Ingress should now point to production services:
# - http://192.168.20.11:3000  (website)
# - http://192.168.20.10:8001  (API)
# etc.

# Restart cloudflared
sudo systemctl restart cloudflared
```

### Step 4.3: Update nginx Configuration

```bash
# On myca-website VM
ssh myca@192.168.20.11

# Copy nginx config
sudo cp /opt/myca/config/nginx/mycosoft.conf /etc/nginx/sites-available/mycosoft

# Update upstream addresses if needed
sudo nano /etc/nginx/sites-available/mycosoft

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4.4: Update Vault Secrets

```bash
# Update database credentials
vault kv put secret/myca/database/postgres \
  username=mas \
  password=$(openssl rand -base64 32)

# Update with actual production passwords
vault kv put secret/myca/integrations/proxmox \
  token_id="myca@pam!automation" \
  token_secret="<production-secret>"
```

### Configuration Checklist

| Config File | Updated | Tested |
|-------------|---------|--------|
| .env | [ ] | [ ] |
| cloudflared config | [ ] | [ ] |
| nginx config | [ ] | [ ] |
| Vault secrets | [ ] | [ ] |
| docker-compose.yml | [ ] | [ ] |

---

## Phase 5: Service Deployment

### Step 5.1: Start Core Services

```bash
# On myca-core VM
cd /opt/myca

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Step 5.2: Verify Services

```bash
# MYCA API
curl http://localhost:8001/health
# Expected: {"status": "healthy"}

# MINDEX
curl http://localhost:8000/health

# n8n
curl http://localhost:5678/healthz
```

### Step 5.3: Start Website

```bash
# On myca-website VM
cd /opt/myca

# Build and start
npm install
npm run build
pm2 start ecosystem.config.js

# Or with Docker
docker compose -f docker-compose.website.yml up -d
```

### Step 5.4: Configure Systemd Services

```bash
# Enable auto-start
sudo systemctl enable myca-orchestrator
sudo systemctl start myca-orchestrator

# Verify
sudo systemctl status myca-orchestrator
```

### Service Deployment Checklist

| Service | Started | Health Check | Logs Clean |
|---------|---------|--------------|------------|
| MYCA API | [ ] | [ ] | [ ] |
| MINDEX | [ ] | [ ] | [ ] |
| n8n | [ ] | [ ] | [ ] |
| Website | [ ] | [ ] | [ ] |
| PostgreSQL | [ ] | [ ] | [ ] |
| Redis | [ ] | [ ] | [ ] |
| Qdrant | [ ] | [ ] | [ ] |
| cloudflared | [ ] | [ ] | [ ] |

---

## Phase 6: DNS Cutover

### Step 6.1: Pre-Cutover Verification

Before switching DNS:

- [ ] All services running on production
- [ ] Health checks passing
- [ ] Cloudflare tunnel connected
- [ ] SSL certificates valid

### Step 6.2: Update Cloudflare DNS

```bash
# Verify tunnel is routing correctly
cloudflared tunnel info mycosoft-tunnel

# DNS should already point to tunnel
# No changes needed if tunnel is properly configured
```

### Step 6.3: Verify External Access

```bash
# Test from external network
curl -I https://mycosoft.com
curl -I https://api.mycosoft.com/health
curl -I https://dashboard.mycosoft.com
```

### Step 6.4: Monitor Traffic

```bash
# Watch cloudflared logs
sudo journalctl -u cloudflared -f

# Watch nginx access logs
sudo tail -f /var/log/nginx/access.log
```

### DNS Cutover Checklist

| Domain | Resolves | SSL Valid | Response |
|--------|----------|-----------|----------|
| mycosoft.com | [ ] | [ ] | [ ] |
| www.mycosoft.com | [ ] | [ ] | [ ] |
| api.mycosoft.com | [ ] | [ ] | [ ] |
| dashboard.mycosoft.com | [ ] | [ ] | [ ] |
| webhooks.mycosoft.com | [ ] | [ ] | [ ] |

---

## Post-Migration Verification

### Functional Testing

- [ ] **Website loads correctly**
  - Home page renders
  - All assets load
  - No console errors

- [ ] **API endpoints work**
  ```bash
  curl https://api.mycosoft.com/agents
  curl https://api.mycosoft.com/health
  ```

- [ ] **Database connectivity**
  ```bash
  # From myca-core
  docker exec myca-api python -c "from mycosoft_mas.core.db import test_connection; test_connection()"
  ```

- [ ] **Agent operations**
  ```bash
  curl -X POST https://api.mycosoft.com/agents/run -H "Authorization: Bearer <token>"
  ```

### Performance Verification

- [ ] **Response times acceptable**
  ```bash
  ab -n 100 -c 10 https://mycosoft.com/
  ```

- [ ] **No memory leaks**
  ```bash
  docker stats
  ```

- [ ] **Database performance**
  ```bash
  docker exec myca-postgres pg_stat_activity
  ```

### Security Verification

- [ ] **SSL Grade A+**
  - Test at https://www.ssllabs.com/ssltest/

- [ ] **Security headers present**
  ```bash
  curl -I https://mycosoft.com | grep -i "x-frame\|x-content\|strict-transport"
  ```

- [ ] **No exposed sensitive data**
  - Check for leaked secrets
  - Verify debug mode off

### Final Checklist

| Category | Item | Status |
|----------|------|--------|
| Functional | Website | [ ] |
| Functional | API | [ ] |
| Functional | Dashboard | [ ] |
| Performance | Response time < 500ms | [ ] |
| Performance | No memory leaks | [ ] |
| Security | SSL Grade A+ | [ ] |
| Security | Headers present | [ ] |
| Monitoring | Alerts working | [ ] |
| Backup | Scheduled | [ ] |

---

## Rollback Plan

### When to Rollback

Rollback if:
- Critical functionality broken
- Data corruption detected
- Security vulnerability exposed
- Performance unacceptable

### Rollback Steps

#### Step 1: Stop Production Services

```bash
# On production VMs
docker compose down
sudo systemctl stop cloudflared
```

#### Step 2: Restore DNS

If using separate staging tunnel:
```bash
# Point DNS back to development tunnel
cloudflared tunnel route dns dev-tunnel mycosoft.com
```

#### Step 3: Start Development Services

```powershell
# On mycocomp
docker compose up -d
```

#### Step 4: Verify Development Running

```powershell
curl http://localhost:3000
curl http://localhost:8001/health
```

#### Step 5: Investigate and Fix

- Document what went wrong
- Fix issues
- Plan re-migration

### Rollback Timeline

| Time | Action |
|------|--------|
| 0-5 min | Identify issue, decide to rollback |
| 5-10 min | Stop production services |
| 10-15 min | Switch DNS/tunnel |
| 15-20 min | Start development services |
| 20-30 min | Verify development working |
| 30+ min | Investigate root cause |

---

## Troubleshooting

### Service Won't Start

```bash
# Check container logs
docker compose logs <service>

# Check system resources
df -h
free -m

# Check for port conflicts
netstat -tlnp | grep <port>
```

### Database Connection Failed

```bash
# Verify database container running
docker ps | grep postgres

# Test connection
docker exec myca-api python -c "import psycopg2; psycopg2.connect('...')"

# Check firewall
sudo ufw status
```

### Website 502 Error

```bash
# Check nginx config
sudo nginx -t

# Check upstream service
curl http://127.0.0.1:3000

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Cloudflare Tunnel Issues

```bash
# Check tunnel status
cloudflared tunnel info mycosoft-tunnel

# Check service
sudo systemctl status cloudflared

# View detailed logs
sudo journalctl -u cloudflared -n 100
```

### Data Not Migrated

```bash
# Verify NAS mount
mount | grep mycosoft

# Check file permissions
ls -la /mnt/mycosoft/databases/

# Reimport from backup
# See Phase 2 steps
```

---

## Migration Log Template

Use this template to document the migration:

```markdown
# Migration Log - [Date]

## Team
- Lead: 
- Participants: 

## Timeline
| Time | Action | Status | Notes |
|------|--------|--------|-------|
| 00:00 | Started migration | | |
| | | | |

## Issues Encountered
1. Issue: 
   Resolution: 
   Time lost: 

## Post-Migration Status
- [ ] All services running
- [ ] All tests passing
- [ ] Monitoring active
- [ ] Backups scheduled

## Lessons Learned
1. 
2. 

## Follow-up Tasks
1. 
2. 
```

---

## Related Documents

- [MASTER_SETUP_GUIDE.md](./MASTER_SETUP_GUIDE.md) - Overall architecture
- [PROXMOX_VM_DEPLOYMENT.md](./PROXMOX_VM_DEPLOYMENT.md) - VM configuration
- [TESTING_DEBUGGING_PROCEDURES.md](./TESTING_DEBUGGING_PROCEDURES.md) - Testing procedures
- [scripts/deploy_production.ps1](../../scripts/deploy_production.ps1) - Automated deployment

---

*Document maintained by MYCA Infrastructure Team*
