# Always-On Services: Local Dev vs VM Production (Feb 12, 2026)

Single reference for what must always run locally (Docker Desktop) for testing and on VMs for production, with clear communication paths.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOCAL DEV MACHINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Next.js Dev Server (3010)  ──┐                                              │
│  MycoBrain Service (8003)   ──┼──→  API calls to VMs                        │
│  n8n Docker (5678)          ──┘                                              │
│  Cursor Sync Watcher                                                         │
│  Notion Docs Watcher                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   VM 187 - Sandbox  │  │   VM 188 - MAS      │  │   VM 189 - MINDEX   │
│   192.168.0.187     │  │   192.168.0.188     │  │   192.168.0.189     │
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ Website (3000)      │  │ MAS Orchestrator    │  │ PostgreSQL (5432)   │
│ Cloudflare Tunnel   │  │ (8001)              │  │ Redis (6379)        │
│ Mycorrhizae (8002)  │  │ n8n (5678)          │  │ Qdrant (6333)       │
│                     │  │ Ollama (11434)      │  │ MINDEX API (8000)   │
│                     │  │ Prometheus (9090)   │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## Environment 1: Local Dev (Docker Desktop)

### Required Always-On (start every session)

| Service | Port | Docker? | Start Command |
|---------|------|---------|---------------|
| **MycoBrain Service** | 8003 | No | `.\scripts\mycobrain-service.ps1 start` |
| **n8n Local** | 5678 | Yes | `.\scripts\n8n-healthcheck.ps1 -StartDocker -StartLocal` |
| **Cursor Sync Watcher** | - | No | `python scripts/sync_cursor_system.py --watch` |
| **Notion Docs Watcher** | - | No | `.\scripts\notion-sync.ps1 watch-bg` |

### One Command to Start All

```powershell
.\scripts\start-dev-environment.ps1
```

Or use the autostart healthcheck:

```powershell
.\scripts\autostart-healthcheck.ps1 -StartMissing
```

### Docker Desktop Requirement

Docker Desktop must be running for:
- n8n local container
- Full-stack testing (optional)

When NOT needed:
- Website development (use `npm run dev:next-only` on port 3010)
- API testing (connect to VMs directly)

### Local .env.local Configuration

In `WEBSITE/website/.env.local`:

```env
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
NEXT_PUBLIC_MAS_API_URL=http://192.168.0.188:8001
```

---

## Environment 2: VM Production (Always-On)

### VM 187 - Sandbox (192.168.0.187)

| Service | Port | Container | Always On |
|---------|------|-----------|-----------|
| Website | 3000 | `mycosoft-website` | Yes |
| Cloudflare Tunnel | - | - | Yes |
| Mycorrhizae API | 8002 | `mycorrhizae-api` | Yes |

**Health check:** `curl -s http://192.168.0.187:3000`

**Restart website:**
```bash
ssh mycosoft@192.168.0.187
docker restart mycosoft-website
```

### VM 188 - MAS (192.168.0.188)

| Service | Port | Type | Always On |
|---------|------|------|-----------|
| **MAS Orchestrator** | 8001 | systemd | Yes |
| n8n Workflows | 5678 | Docker | Yes |
| Ollama LLM | 11434 | Docker | Yes |
| Prometheus | 9090 | Docker | Yes |

**Health check:** `curl -s http://192.168.0.188:8001/health`

**Restart MAS:**
```bash
ssh mycosoft@192.168.0.188
sudo systemctl restart mas-orchestrator
```

### VM 189 - MINDEX (192.168.0.189)

| Service | Port | Container | Always On |
|---------|------|-----------|-----------|
| **PostgreSQL** | 5432 | `mindex-postgres` | Yes |
| **Redis** | 6379 | `mindex-redis` | Yes |
| **Qdrant** | 6333 | `mindex-qdrant` | Yes |
| MINDEX API | 8000 | `mindex-api` | Yes |

**Health check:** `curl -s http://192.168.0.189:8000/`

**Restart all:**
```bash
ssh mycosoft@192.168.0.189
cd /opt/mycosoft/mindex && docker compose restart
```

---

## Deployment Prerequisites

### Services Required for Deployment

| To Deploy | Required Running |
|-----------|------------------|
| Website (187) | Docker on 187, NAS mount |
| MAS (188) | PostgreSQL (189), Redis (189) |
| MINDEX (189) | PostgreSQL, Redis, Qdrant |

### Deployment Commands

```powershell
# Deploy Website (full rebuild)
python WEBSITE/website/_rebuild_sandbox.py

# Deploy MAS
python MAS/mycosoft-mas/_rebuild_mas_container.py

# Deploy MINDEX
python MAS/mycosoft-mas/_deploy_mindex_api.py
```

### Post-Deployment (Mandatory)

- Purge Cloudflare cache after website deployment
- Verify health endpoints after any VM deployment

---

## Communication Flow

```
Local Dev (3010) ──► MAS (8001) ──► PostgreSQL (5432)
                           │
                           ├──► Redis (6379)
                           │
                           ├──► Qdrant (6333)
                           │
                           └──► MINDEX (8000) ──► PostgreSQL/Redis/Qdrant

Website (3000) ──► MAS (8001) ──► All backends
       │
       └──► MINDEX (8000) ──► All backends

MycoBrain (8003) ──► MAS (8001) ──► Device registry, heartbeats
```

---

## Health Check Commands

### Local

```powershell
# Check all autostart services
.\scripts\autostart-healthcheck.ps1

# Check dev environment status
.\scripts\start-dev-environment.ps1 -Status

# Check MycoBrain specifically
.\scripts\mycobrain-service.ps1 health

# Check n8n
curl -s http://localhost:5678/healthz
```

### VMs

```powershell
# Quick health check all VMs
.\scripts\check-all-environments.ps1

# Individual checks
curl -s http://192.168.0.188:8001/health  # MAS
curl -s http://192.168.0.189:8000/        # MINDEX
curl -s http://192.168.0.187:3000         # Website

# Detailed MAS health
Invoke-RestMethod http://192.168.0.188:8001/health | ConvertTo-Json
```

---

## Summary Table

| Environment | Service | Port | Docker | Always On |
|-------------|---------|------|--------|-----------|
| **Local** | MycoBrain Service | 8003 | No | Yes |
| **Local** | n8n | 5678 | Yes | Yes |
| **Local** | Cursor Sync | - | No | Yes |
| **Local** | Notion Watcher | - | No | Yes |
| **VM 187** | Website | 3000 | Yes | Yes |
| **VM 187** | Mycorrhizae API | 8002 | Yes | Yes |
| **VM 188** | MAS Orchestrator | 8001 | No (systemd) | Yes |
| **VM 188** | n8n | 5678 | Yes | Yes |
| **VM 188** | Ollama | 11434 | Yes | Yes |
| **VM 188** | Prometheus | 9090 | Yes | Yes |
| **VM 189** | PostgreSQL | 5432 | Yes | Yes |
| **VM 189** | Redis | 6379 | Yes | Yes |
| **VM 189** | Qdrant | 6333 | Yes | Yes |
| **VM 189** | MINDEX API | 8000 | Yes | Yes |

---

## Quick Reference

### Start Local Dev

```powershell
.\scripts\start-dev-environment.ps1
cd ..\WEBSITE\website
npm run dev:next-only
```

### Check Everything

```powershell
.\scripts\check-all-environments.ps1
```

### Deploy Updates

```powershell
# Website
python WEBSITE/website/_rebuild_sandbox.py
# Then purge Cloudflare cache

# MAS
python _rebuild_mas_container.py

# MINDEX
python _deploy_mindex_api.py
```

---

## Related Documentation

- [VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md](VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md) - Detailed VM layout
- [DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md](DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md) - Deployment workflow
- [TERMINAL_AND_PYTHON_OPERATIONS_GUIDE_FEB12_2026.md](TERMINAL_AND_PYTHON_OPERATIONS_GUIDE_FEB12_2026.md) - Process management
- `.cursor/rules/autostart-services.mdc` - Autostart service registry
- `.cursor/rules/python-process-registry.mdc` - Full process registry
