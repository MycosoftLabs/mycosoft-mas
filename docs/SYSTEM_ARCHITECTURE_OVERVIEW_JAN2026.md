# Mycosoft System Architecture Overview

**Version**: 1.1  
**Last Updated**: January 21, 2026  
**Purpose**: Complete reference for all Mycosoft infrastructure and services

---

## 🌐 Physical Network Topology

> **Updated January 21, 2026**: Infrastructure recabled with fiber optic router, 10Gig switch, and reorganized server connections.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INTERNET (WAN)                                        │
│                                         │                                                │
│                                   ISP Fiber ONT                                          │
│                                    (10 Gbps)                                             │
└─────────────────────────────────────────┼───────────────────────────────────────────────┘
                                          │
                                    ┌─────▼─────┐
                                    │  FIBER    │
                                    │  ROUTER   │
                                    │192.168.0.1│
                                    │ (10 Gbps) │
                                    └─────┬─────┘
                                          │ CAT 8 / Fiber (10 Gbps)
                                          │
                              ┌───────────▼───────────┐
                              │   8-PORT 10G SWITCH   │
                              │     192.168.0.2       │
                              │  (10 Gbps Backbone)   │
                              └───┬───┬───┬───┬───┬───┘
                                  │   │   │   │   │
          ┌───────────────────────┘   │   │   │   └────────────────────────┐
          │                           │   │   │                            │
    ┌─────▼─────┐              ┌─────▼───▼───▼─────┐               ┌──────▼──────┐
    │  DREAM    │              │   DELL SERVERS    │               │     NAS     │
    │  MACHINE  │              │  (PROXMOX HOSTS)  │               │192.168.0.105│
    │192.168.0.3│              │                   │               │  (2.5 Gbps) │
    │ (2.5 Gbps)│              │ ┌───────────────┐ │               └─────────────┘
    └─────┬─────┘              │ │ 192.168.0.202 │ │
          │                    │ │ (Primary) 10G │ │    ┌──────────────┐
    ┌─────▼─────┐              │ ├───────────────┤ │    │  WINDOWS PC  │
    │ PoE       │              │ │ 192.168.0.203 │ │    │192.168.0.172 │
    │ SWITCHES  │              │ │(Secondary)10G │ │    │  (2.5 Gbps)  │
    │           │              │ ├───────────────┤ │    └──────────────┘
    │ ⚠️        │              │ │ 192.168.0.204 │ │
    │ BOTTLENECK│              │ │(Tertiary) 10G │ │
    └─────┬─────┘              │ └───────────────┘ │
          │                    └───────────────────┘
    ┌─────▼─────┐                      │
    │  UBIQUITI │              ┌───────▼───────┐
    │  WiFi APs │              │   VIRTUAL     │
    │           │              │   MACHINES    │
    │Expected:  │              │               │
    │ 2.5 Gbps  │              │ VM 103:       │
    │Actual:    │              │ 192.168.0.187 │
    │ ~30 Mbps  │              │ (Sandbox)     │
    │ ❌        │              └───────────────┘
    └───────────┘
```

### Network Speed Path (Current Issue)

```
Fiber Router ──[10 Gbps]──► 10G Switch ──[2.5 Gbps]──► Dream Machine
                                                              │
                                                    ──[1 Gbps?]──► PoE Switch
                                                                        │
                                                              ──[100 Mbps?]──► WiFi APs
                                                                                    │
                                                                           ──[~30 Mbps]──► Clients
                                                                                 ⚠️ BOTTLENECK
```

---

## 🖧 Logical Network Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
│                                  │                                           │
│                          Cloudflare Edge                                     │
│                    ┌─────────────────────────┐                              │
│                    │  DNS + CDN + WAF        │                              │
│                    │  sandbox.mycosoft.com   │                              │
│                    │  mycosoft.com           │                              │
│                    └──────────┬──────────────┘                              │
│                               │ Cloudflare Tunnel                           │
└───────────────────────────────┼─────────────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────────────┐
│                     LOCAL NETWORK (192.168.0.0/24)                          │
│                               │                                              │
│  ┌────────────────────────────┴───────────────────────────────────────┐     │
│  │                    SANDBOX VM (192.168.0.187)                       │     │
│  │                                                                      │     │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │     │
│  │  │ Website :3000   │  │ MINDEX :8000    │  │ MycoBrain :8003 │     │     │
│  │  │ (Next.js)       │  │ (FastAPI)       │  │ (proxied to Win)│     │     │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘     │     │
│  │                                                                      │     │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │     │
│  │  │ PostgreSQL      │  │ Redis           │  │ N8N :5678       │     │     │
│  │  │ PostGIS         │  │                 │  │                 │     │     │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘     │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                  WINDOWS DEV PC (192.168.0.172)                       │   │
│  │                                                                        │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │ Website Dev     │  │ MycoBrain       │  │ Arduino IDE     │       │   │
│  │  │ :3010           │  │ Service :8003   │  │ (Firmware)      │       │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │   │
│  │                              │                                         │   │
│  │                       ┌──────┴──────┐                                 │   │
│  │                       │   COM7      │                                 │   │
│  │                       │ MycoBrain   │                                 │   │
│  │                       │ ESP32-S3    │                                 │   │
│  │                       └─────────────┘                                 │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                  PROXMOX HOSTS (3x Dell Servers)                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │ 192.168.0.202   │  │ 192.168.0.203   │  │ 192.168.0.204   │       │   │
│  │  │ Primary (10G)   │  │ Secondary (10G) │  │ Tertiary (10G)  │       │   │
│  │  │ VM 103: Sandbox │  │ Future VMs      │  │ Future VMs      │       │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                  NAS (192.168.0.105)                                  │   │
│  │  └── \\mycosoft.com\website\assets\ → VM:/opt/mycosoft/media/        │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚢 Service Architecture

### Production Stack (Always-On)

| Service | Port | Container | Purpose |
|---------|------|-----------|---------|
| **Mycosoft Website** | 3000 | mycosoft-website | Main website (Next.js) |
| **MINDEX API** | 8000 | mindex-api | Mycology index search |
| **MINDEX PostgreSQL** | 5432 | mindex-postgres | PostGIS database |
| **MycoBrain** | 8003 | N/A (Windows) | IoT device management |

### Development Stack (On-Demand)

| Service | Port | Container | Purpose |
|---------|------|-----------|---------|
| **MYCA Dashboard** | 3100 | myca-dashboard | Agent monitoring UI |
| **N8N** | 5678 | mas-n8n-1 | Workflow automation |
| **Grafana** | 3002 | grafana | Metrics visualization |
| **Prometheus** | 9090 | prometheus | Metrics collection |
| **Qdrant** | 6345 | qdrant | Vector database |
| **Redis** | 6390 | mas-redis-1 | Cache layer |
| **Whisper** | 8765 | whisper | Speech-to-text |
| **Ollama** | 11434 | ollama | Local LLM |

---

## 📁 Directory Structure

### Sandbox VM (/opt/mycosoft/)

```
/opt/mycosoft/
├── docker-compose.yml           # Main compose file
├── .env                         # Environment variables
├── website/                     # Website git repo
│   ├── app/                     # Next.js app directory
│   ├── components/              # React components
│   ├── lib/                     # Utilities
│   ├── public/                  # Static assets (small files)
│   ├── services/
│   │   └── mycobrain/           # MycoBrain Python service
│   └── Dockerfile.container     # Production Dockerfile
├── mas/                         # MAS git repo
│   ├── docs/                    # Documentation
│   ├── scripts/                 # Automation scripts
│   └── docker-compose.always-on.yml
├── mindex/                      # MINDEX service
└── media/
    └── website/
        └── assets/              # Media files (NAS-mounted)
            └── mushroom1/       # Per-device folders
```

### Windows Dev PC

```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\
├── WEBSITE\website\             # Website development
│   ├── app/
│   ├── components/
│   ├── services\mycobrain\      # MycoBrain service
│   └── public\assets\           # Local test assets
└── MAS\mycosoft-mas\           # MAS repository
    ├── docs/                    # All documentation
    ├── scripts/                 # Deployment scripts
    └── ...
```

---

## 🔀 Request Flow

### Website Request (sandbox.mycosoft.com/devices)

```
Browser → Cloudflare CDN → Cloudflare Tunnel → VM:3000 → Next.js Server
                                                              ↓
                                                    Server Component
                                                              ↓
                                                    HTML Response
```

### MycoBrain API Request (sandbox.mycosoft.com/api/mycobrain/*)

```
Browser → Cloudflare → Tunnel → VM → Cloudflare Config Routes to:
                                        ↓
                              Windows PC:18003 (MycoBrain Service)
                                        ↓
                                      COM7
                                        ↓
                                  ESP32-S3 Board
```

### Media Asset Request (sandbox.mycosoft.com/assets/*)

```
Browser → Cloudflare CDN (cache check)
                  ↓ (cache miss)
         Cloudflare Tunnel
                  ↓
         VM:3000/assets/*
                  ↓
         Next.js static server
                  ↓
         /app/public/assets/ (container)
                  ↓
         Volume mount from host
                  ↓
         /opt/mycosoft/media/website/assets/
                  ↓
         NAS mount (//192.168.0.105/mycosoft.com)
```

---

## 🔐 Authentication Flow

### Supabase Auth (Website Login)

```
1. User clicks "Sign In"
2. Frontend redirects to Supabase Auth UI
3. User authenticates (OAuth or Email)
4. Supabase redirects back with tokens
5. Frontend stores session in cookies
6. Server components read session via Supabase client
```

### MycoBrain API Auth (Internal)

```
Currently: No auth (local network only)
Future: API key or JWT validation
```

---

## 🗄️ Data Storage

### PostgreSQL Databases

| Database | Purpose | Location |
|----------|---------|----------|
| **mindex** | Mycology index, species data | VM:5432 |
| **supabase** | User data, auth | Cloud (Supabase) |

### File Storage

| Type | Location | Purpose |
|------|----------|---------|
| **Media** | NAS → VM | Videos, large images |
| **Static** | Git → Container | Icons, small images |
| **Telemetry** | MINDEX DB | Sensor history |

---

## 🔧 Key Environment Variables

### Website (Required at Build Time)

```bash
# Supabase (CRITICAL - must be in ARG during docker build)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# NextAuth
NEXTAUTH_URL=https://sandbox.mycosoft.com
NEXTAUTH_SECRET=<secret>
```

### MycoBrain Service

```bash
MINDEX_API_URL=http://192.168.0.187:8000
MINDEX_API_KEY=local-dev-key
MYCOBRAIN_PUSH_TELEMETRY_TO_MINDEX=true
```

---

## 🚀 Deployment Workflows

### Code Change Deployment

```
1. Test locally (npm run dev, localhost:3010)
2. Commit and push to GitHub
3. SSH to VM
4. git reset --hard origin/main
5. docker compose build --no-cache
6. docker compose up -d --force-recreate
7. Purge Cloudflare cache
8. Verify sandbox.mycosoft.com
```

### Media-Only Deployment

```
1. Copy files to NAS (\\192.168.0.105\mycosoft.com\website\assets\)
2. docker restart mycosoft-website (on VM)
3. Purge Cloudflare cache (if stale)
4. Verify asset URLs
```

---

## 📊 Monitoring & Observability

### Health Endpoints

| Service | URL | Check |
|---------|-----|-------|
| Website | /api/health | 200 OK |
| MINDEX | /health | {"status": "ok"} |
| MycoBrain | /health | {"devices_connected": N} |

### Logs

| Service | Command |
|---------|---------|
| Website | `docker logs mycosoft-website -f` |
| MINDEX | `docker logs mindex-api -f` |
| Tunnel | `journalctl -u cloudflared -f` |

---

## 🐛 Common Issues Reference

| Issue | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| 502 Bad Gateway | Cloudflare routing wrong | Stop Windows cloudflared |
| 500 on all pages | Missing Supabase env | Rebuild with build args |
| /assets/* 404 | Next.js cache | docker restart |
| MycoBrain frozen | Duplicate process | Kill duplicate, reconnect |
| Login fails | Supabase config | Check env vars |

---

## 📚 Documentation Map

### Getting Started
- `docs/QUICKSTART.md` - New developer setup
- `docs/DEPLOYMENT_INSTRUCTIONS_MASTER.md` - Deployment reference

### Operations
- `docs/MYCOBRAIN_TROUBLESHOOTING_GUIDE.md` - Device issues
- `docs/RUNBOOK_NAS_MEDIA_WEBSITE_ASSETS.md` - Media deployment
- `docs/VM_MAINTENANCE_CHECKLIST.md` - VM maintenance

### Architecture
- `docs/SYSTEM_ARCHITECTURE_OVERVIEW_JAN2026.md` - This document
- `docs/MASTER_ARCHITECTURE.md` - Detailed architecture

### Session Logs
- `docs/SESSION_SUMMARY_JAN20_2026.md` - Today's work
- `docs/STAFF_BRIEFING_JAN20_2026.md` - Staff summary

---

## 🔗 Related Systems

| System | Purpose | Access |
|--------|---------|--------|
| **GitHub** | Source control | github.com/MycosoftLabs |
| **Supabase** | Auth & DB | supabase.com/dashboard |
| **Cloudflare** | DNS & Tunnel | dash.cloudflare.com |
| **Proxmox** | VM management | 192.168.0.202:8006 |

---

*Document Version: 1.0*  
*Created: January 20, 2026*  
*Maintainer: Mycosoft Development Team*
