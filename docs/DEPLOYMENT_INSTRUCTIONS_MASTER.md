# Mycosoft Deployment Instructions — Master Reference

**Version**: 1.0  
**Last Updated**: January 19, 2026  
**Audience**: All agents, developers, and automation systems working on Mycosoft

---

## ⚠️ CRITICAL: READ BEFORE ANY DEPLOYMENT

This document is the **single source of truth** for deploying changes to Mycosoft systems. Every agent and developer **MUST** follow these procedures exactly.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Golden Rules](#2-golden-rules)
3. [Environment Variables](#3-environment-variables)
4. [Website Deployment](#4-website-deployment)
5. [Media Assets Deployment](#5-media-assets-deployment)
6. [Docker Compose Stacks](#6-docker-compose-stacks)
7. [Cloudflare Configuration](#7-cloudflare-configuration)
8. [Verification Checklist](#8-verification-checklist)
9. [Common Failure Modes](#9-common-failure-modes)
10. [Troubleshooting Guide](#10-troubleshooting-guide)

---

## 1. Architecture Overview

### Infrastructure Map

| System | Location | IP Address | Purpose |
|--------|----------|------------|---------|
| **Windows Dev PC** | Local | 192.168.0.172 | Development, MycoBrain service |
| **Sandbox VM (103)** | Proxmox | 192.168.0.187 | Staging environment |
| **Proxmox Host** | Local | 192.168.0.202 | VM hypervisor |
| **Cloudflare** | Cloud | - | DNS, Tunnel, CDN |
| **Supabase** | Cloud | - | Auth, Database |
| **GitHub** | Cloud | - | Source control |

### Port Assignments

| Port | Service | Stack |
|------|---------|-------|
| 3000 | Mycosoft Website | Always-On |
| 3010 | Website Dev (localhost) | Development |
| 3100 | MYCA Dashboard | MAS |
| 5678 | N8N | MAS |
| 8000 | MINDEX API | Always-On |
| 8003 | MycoBrain Service | Always-On |
| 9090 | Prometheus | MAS |
| 3002 | Grafana | MAS |

### Directory Structure on VM

```
/opt/mycosoft/
├── docker-compose.yml           # Main compose file (project: mycosoft-production)
├── docker-compose.always-on.yml # Always-on services
├── .env                         # Environment variables
├── website/                     # Website source (git repo)
├── mas/                         # MAS source (git repo)
├── mindex/                      # MINDEX source
└── media/
    └── website/
        └── assets/              # Media files (mounted into containers)

/home/mycosoft/
├── .cloudflared/
│   └── config.yml               # Cloudflare tunnel configuration
└── mycosoft/
    └── mas/
        └── .env                 # MAS environment variables
```

---

## 2. Golden Rules

### NEVER Do These:

1. **NEVER use mock data** — All systems use real data only
2. **NEVER skip Docker rebuild** — Hot reload doesn't work in production containers
3. **NEVER forget to clear Cloudflare cache** — Stale assets will persist
4. **NEVER rely on runtime env alone for `NEXT_PUBLIC_*`** — Must be set at build time
5. **NEVER run cloudflared on both Windows AND VM** — Only ONE connector per tunnel

### ALWAYS Do These:

1. **ALWAYS test on localhost first** — Verify before pushing
2. **ALWAYS rebuild Docker image with `--no-cache`** — Ensures clean builds
3. **ALWAYS verify deployment** — Check URLs after every deployment
4. **ALWAYS read recent docs first** — Check docs created in last 72 hours before starting work
5. **ALWAYS document changes** — Update relevant MD files after work

---

## 3. Environment Variables

### Critical: Build-Time vs Runtime Variables

**Next.js Quirk**: `NEXT_PUBLIC_*` variables are embedded into the client bundle at **build time**, NOT runtime.

This means:
- Setting `NEXT_PUBLIC_SUPABASE_URL` in docker-compose `environment:` is **NOT ENOUGH**
- You **MUST** pass them as `build.args` in docker-compose AND as `ARG`/`ENV` in Dockerfile

### Required Dockerfile Pattern

```dockerfile
# Build stage
FROM node:20-alpine AS builder

# These MUST be declared as ARG to receive from docker-compose
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# These MUST be set as ENV so npm run build can access them
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}

# Build happens here with env vars embedded
RUN npm run build
```

### Required docker-compose Pattern

```yaml
mycosoft-website:
  build:
    context: ./website
    dockerfile: Dockerfile.container
    args:
      - NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
  environment:
    # Runtime env (for server-side code only)
    - NODE_ENV=production
    - NEXTAUTH_URL=https://sandbox.mycosoft.com
```

### Environment Files on VM

**Location**: `/home/mycosoft/mycosoft/mas/.env`

Required variables:
```bash
# Supabase (CRITICAL - needed at build time)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOi...

# NextAuth
NEXTAUTH_URL=https://sandbox.mycosoft.com
NEXTAUTH_SECRET=<secret>

# Database
DATABASE_URL=postgresql://...

# API Keys
OPENAI_API_KEY=sk-...
```

---

## 4. Website Deployment

### Standard Deployment Flow

```
┌─────────────────┐    ┌─────────────┐    ┌─────────────────┐    ┌──────────────┐
│ 1. Local Test   │ → │ 2. Git Push │ → │ 3. VM Pull/Build│ → │ 4. Verify    │
│    localhost    │    │   GitHub    │    │    SSH + Docker │    │   sandbox    │
└─────────────────┘    └─────────────┘    └─────────────────┘    └──────────────┘
```

### Step-by-Step Commands

#### Step 1: Test Locally (Windows Dev PC)

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev
# Open http://localhost:3010 and verify changes
```

#### Step 2: Commit and Push to GitHub

```powershell
git add .
git commit -m "feat: description of change"
git push origin main
```

#### Step 3: SSH to VM and Pull Code

```bash
ssh mycosoft@192.168.0.187
# Password: Mushroom1!Mushroom1!

cd /opt/mycosoft/website
git fetch origin main
git reset --hard origin/main
```

#### Step 4: Rebuild Docker Image (CRITICAL)

```bash
cd /opt/mycosoft

# Option A: Using always-on compose file
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache

# Option B: Using main compose file
docker compose -p mycosoft-production build mycosoft-website --no-cache
```

#### Step 5: Restart Container

```bash
# Option A: Using always-on compose
docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website

# Option B: Using main compose
docker compose -p mycosoft-production up -d mycosoft-website
```

#### Step 6: Clear Cloudflare Cache

1. Go to https://dash.cloudflare.com
2. Select `mycosoft.com` domain
3. Caching → Configuration → **Purge Everything**

#### Step 7: Verify Deployment

```bash
# On VM
curl -s http://localhost:3000 | head -20

# In browser
# https://sandbox.mycosoft.com
```

---

## 5. Media Assets Deployment

### Fast Path (No Rebuild Required)

For videos, images, and other media files, you **do NOT** need to rebuild the Docker image.

### Architecture

```
Windows Dev PC                      Sandbox VM
─────────────────                   ──────────────────────────
WEBSITE/public/assets/   ─sync→    /opt/mycosoft/media/website/assets/
                                         ↓
                                   (volume mount, read-only)
                                         ↓
                                   Container: /app/public/assets/
                                         ↓
                                   URL: /assets/...
```

### Sync Media to VM

Option 1: Use Paramiko script
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/media/sync_website_media_paramiko.py
```

Option 2: Manual SCP
```powershell
scp -r "C:\path\to\assets\*" mycosoft@192.168.0.187:/opt/mycosoft/media/website/assets/
```

### CRITICAL: Restart Required After Sync

Next.js standalone mode caches the `public/` directory. New files won't be served until restart.

```bash
docker restart mycosoft-website
```

### Verify Media

```bash
# On VM
curl -I http://localhost:3000/assets/mushroom1/Main%20A.jpg
# Should return: HTTP/1.1 200 OK

# In browser
# https://sandbox.mycosoft.com/assets/mushroom1/Main%20A.jpg
```

### Handling Filename Mismatches

If code expects a different filename than what exists on disk, create a symlink:

```bash
cd /opt/mycosoft/media/website/assets/mushroom1
ln -s "mushroom 1 walking.mp4" "Walking.mp4"
```

---

## 6. Docker Compose Stacks

### Always-On Stack (`docker-compose.always-on.yml`)

Services that run 24/7:

| Service | Port | Description |
|---------|------|-------------|
| mycosoft-website | 3000 | Main website |
| mindex-api | 8000 | MINDEX search API |
| mycobrain-service | 8003 | MycoBrain IoT service |
| mindex-postgres | 5432 | PostGIS database |

Start/Stop:
```bash
docker compose -f docker-compose.always-on.yml up -d
docker compose -f docker-compose.always-on.yml down
```

### MAS Stack (`docker-compose.yml`)

Optional services for development/testing:

| Service | Port | Description |
|---------|------|-------------|
| mas-orchestrator | 8001 | Agent orchestrator |
| grafana | 3002 | Monitoring dashboards |
| prometheus | 9090 | Metrics collection |
| n8n | 5678 | Workflow automation |
| qdrant | 6345 | Vector database |
| redis | 6390 | Cache |
| whisper | 8765 | Speech-to-text |
| ollama | 11434 | Local LLM |
| myca-dashboard | 3100 | MYCA UI |

Start/Stop:
```bash
docker compose -p mycosoft-production up -d
docker compose -p mycosoft-production down
```

---

## 7. Cloudflare Configuration

### Tunnel Configuration Location

```
/home/mycosoft/.cloudflared/config.yml
```

### Current Routes

```yaml
ingress:
  - hostname: sandbox.mycosoft.com
    path: /api/mycobrain.*
    service: http://192.168.0.172:18003  # Windows LAN service (MycoBrain; avoids 8003 conflicts on Windows)
    
  - hostname: sandbox.mycosoft.com
    path: /api/mindex.*
    service: http://localhost:8000       # VM container
    
  - hostname: sandbox.mycosoft.com
    service: http://localhost:3000       # Website (default)
    
  - service: http_status:404             # Catch-all
```

### Restart Tunnel

```bash
sudo systemctl restart cloudflared
```

### Check Tunnel Status

```bash
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f
```

### CRITICAL: Only ONE Connector Per Tunnel

The same tunnel token may be installed on multiple machines. Cloudflare will route to whichever connector is "active".

**Problem**: If cloudflared is running on Windows AND VM, requests may route to Windows (which doesn't have the containers).

**Solution**:

1. Check Windows for cloudflared:
   ```powershell
   Get-Process cloudflared -ErrorAction SilentlyContinue
   ```

2. If running, STOP IT:
   ```powershell
   taskkill /F /IM cloudflared.exe
   sc.exe stop cloudflared
   ```

3. Verify in Cloudflare Zero Trust Dashboard:
   - Connector should show IP: `192.168.0.187` (VM)
   - Platform: `linux_amd64`
   - NOT: `192.168.0.172` (Windows)

4. Restart VM tunnel:
   ```bash
   sudo systemctl restart cloudflared
   ```

---

## 8. Verification Checklist

### After Every Deployment

| Check | Command/URL | Expected |
|-------|-------------|----------|
| Container running | `docker ps \| grep website` | STATUS: Up |
| Health endpoint | `curl localhost:3000/api/health` | 200 OK |
| Homepage | https://sandbox.mycosoft.com | Page loads |
| Devices page | https://sandbox.mycosoft.com/devices | Images load |
| Mushroom 1 | https://sandbox.mycosoft.com/devices/mushroom-1 | Videos play |
| Static asset | https://sandbox.mycosoft.com/placeholder.svg | 200 OK |
| Media asset | https://sandbox.mycosoft.com/assets/mushroom1/Main%20A.jpg | 200 OK |

### API Endpoints

| Check | URL | Expected |
|-------|-----|----------|
| MINDEX | https://sandbox.mycosoft.com/api/mindex/health | 200 OK |
| MycoBrain | https://sandbox.mycosoft.com/api/mycobrain/ports | 200 OK |

---

## 9. Common Failure Modes

### 1. "Port 3000 already allocated"

**Cause**: Another container or process is using port 3000.

**Fix**:
```bash
# Find what's using it
docker ps | grep 3000
# or
lsof -i :3000

# Remove old container
docker rm -f <container_name>

# Start new one
docker compose -f docker-compose.always-on.yml up -d mycosoft-website
```

### 2. "500 Internal Server Error" on all pages

**Cause**: Missing Supabase environment variables.

**Symptoms in logs**:
```
[Supabase] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY
```

**Fix**:
1. Add variables to `.env` file
2. Add `build.args` to docker-compose for `NEXT_PUBLIC_*` vars
3. Add `ARG` + `ENV` to Dockerfile
4. Rebuild with `--no-cache`

### 3. "/assets/* returns 404" even though files exist

**Cause**: Next.js standalone didn't pick up newly-synced files.

**Fix**:
```bash
docker restart mycosoft-website
```

### 4. "502 Bad Gateway" — Tunnel healthy but no requests

**Cause**: Cloudflare routing to wrong connector (Windows instead of VM).

**Fix**:
```powershell
# On Windows
taskkill /F /IM cloudflared.exe
sc.exe stop cloudflared
```
```bash
# On VM
sudo systemctl restart cloudflared
```

### 5. Videos don't play on mobile

**Cause**: Large videos (8K) fail to decode/autoplay on mobile Safari.

**Fix**:
- Use smaller resolution videos for mobile
- Ensure video attributes: `muted`, `playsInline`, `preload="metadata"`
- Implement mobile detection to serve appropriate video

### 6. "npm ci" fails during Docker build

**Cause**: `package-lock.json` out of sync or peer dependency conflicts.

**Fix**: Update Dockerfile to use:
```dockerfile
RUN npm install --legacy-peer-deps
```

### 7. Client shows "Supabase credentials not configured" despite .env

**Cause**: `NEXT_PUBLIC_*` vars not passed at build time.

**Fix**: See [Section 3: Environment Variables](#3-environment-variables)

---

## 10. Troubleshooting Guide

### View Container Logs

```bash
docker logs mycosoft-website --tail 100
docker logs mycosoft-website -f  # Follow live
```

### Enter Container Shell

```bash
docker exec -it mycosoft-website sh
```

### Check Container Environment

```bash
docker exec mycosoft-website env | grep NEXT
```

### Force Fresh Build

```bash
docker compose -f docker-compose.always-on.yml build --no-cache mycosoft-website
docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website
```

### Reset Everything

```bash
# Stop all
docker compose -f docker-compose.always-on.yml down

# Remove images
docker rmi mycosoft-website:latest

# Rebuild from scratch
docker compose -f docker-compose.always-on.yml build --no-cache
docker compose -f docker-compose.always-on.yml up -d
```

### Check Disk Space

```bash
df -h
docker system df
docker system prune -a  # Clean up unused images/containers
```

---

## Quick Reference Card

### Deploy Website Changes

```bash
# 1. Local
npm run dev  # Test at localhost:3010

# 2. Push
git add . && git commit -m "msg" && git push

# 3. VM
ssh mycosoft@192.168.0.187
cd /opt/mycosoft/website && git reset --hard origin/main
cd /opt/mycosoft
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache
docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website

# 4. Cloudflare: Purge Everything
# 5. Verify: sandbox.mycosoft.com
```

### Deploy Media Only

```bash
# 1. Sync files
scp -r assets/* mycosoft@192.168.0.187:/opt/mycosoft/media/website/assets/

# 2. Restart (required for Next.js to serve new files)
ssh mycosoft@192.168.0.187 "docker restart mycosoft-website"

# 3. Verify
curl -I https://sandbox.mycosoft.com/assets/path/to/file.jpg
```

---

## Credentials Reference

| System | User | Password/Token |
|--------|------|----------------|
| VM SSH | mycosoft | Mushroom1!Mushroom1! |
| Proxmox API | myca@pve!mas | ca23b6c8-5746-46c4-8e36-fc6caad5a9e5 |
| Supabase | (dashboard) | See 1Password |
| Cloudflare | (dashboard) | See 1Password |
| GitHub | MycosoftLabs | See 1Password |

---

## Related Documentation

- `docs/SANDBOX_DEPLOYMENT_RUNBOOK.md` - Detailed runbook
- `docs/SANDBOX_DEPLOYMENT_PROCESS.md` - Process details
- `docs/DEPLOYMENT_SESSION_JAN19_2026_TODAY.md` - Today's session notes
- `docs/MEDIA_ASSETS_PIPELINE.md` - Media sync details
- `docs/CLOUDFLARE_TUNNEL_SETUP.md` - Tunnel configuration

---

*Document Version: 1.0*  
*Created: January 19, 2026*  
*Maintainer: Morgan Rockwell / Cursor AI*
