# Server Migration Master Guide

**Version**: 1.0.0  
**Date**: 2026-01-16  
**Purpose**: Complete reference for migrating Mycosoft systems to production servers  
**Priority**: CRITICAL

---

## 🎯 Executive Summary

This document serves as the **master guide** for migrating the entire Mycosoft system to production servers. It consolidates all deployment information from recent sessions.

### System Overview

| Component | Repository | Port | Status |
|-----------|------------|------|--------|
| **Mycosoft Website** | WEBSITE | 3000 | ✅ Production Ready |
| **CREP Dashboard** | WEBSITE | 3000 | ✅ Production Ready |
| **MINDEX API** | WEBSITE | 8000 | ✅ Production Ready |
| **MycoBrain Service** | WEBSITE | 8003 | ✅ Production Ready |
| **MAS Orchestrator** | MAS | 8001 | ✅ Production Ready |
| **N8n Workflows** | MAS | 5678 | ✅ Production Ready |

---

## 📁 Repository Locations

### WEBSITE Repository (PRIMARY)

**Windows Path**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\`

Contains:
- Next.js website (port 3000)
- CREP Dashboard
- NatureOS Dashboard
- Earth Simulator
- MINDEX integration
- MycoBrain integration
- All OEI (Operational Environment Intelligence) components

### MAS Repository (SUPPORTING)

**Windows Path**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\`

Contains:
- Orchestrator service
- N8n workflows
- Agent configurations
- Voice UI services
- Grafana/Prometheus monitoring

---

## 🐳 Docker Container Architecture

### Always-On Stack (docker-compose.always-on.yml)

| Container | Port | Service | Notes |
|-----------|------|---------|-------|
| mycosoft-website | 3000 | Next.js Website | Main application |
| mindex | 8000 | MINDEX API | Fungal database |
| mycobrain | 8003 | MycoBrain Service | Device communication |
| postgres | 5432 | PostgreSQL | Primary database |

### MAS Stack (docker-compose.yml)

| Container | Port | Service | Notes |
|-----------|------|---------|-------|
| mas-orchestrator | 8001 | MAS Orchestrator | Agent management |
| grafana | 3002 | Grafana | Monitoring dashboards |
| prometheus | 9090 | Prometheus | Metrics collection |
| n8n | 5678 | N8n | Workflow automation |
| qdrant | 6345 | Qdrant | Vector database |
| redis | 6390 | Redis | Cache layer |
| whisper | 8765 | Whisper | Speech-to-text |
| piper-tts | 10200 | Piper TTS | Text-to-speech |
| openedai-speech | 5500 | OpenEDAI Speech | Voice synthesis |
| voice-ui | 8090 | Voice UI | Voice interface |
| myca-dashboard | 3100 | MYCA Dashboard | UniFi-style dashboard |
| ollama | 11434 | Ollama | LLM inference |

### CREP Collectors Stack (docker-compose.crep.yml)

| Container | Port | Service | Notes |
|-----------|------|---------|-------|
| crep-carbon-mapper | 8201 | Carbon Mapper | Emission tracking |
| crep-railway | 8202 | Railway | Rail infrastructure |
| crep-astria | 8203 | Astria | Space debris |
| crep-satmap | 8204 | SatMap | Satellites |
| crep-marine | 8205 | Marine | Vessel tracking |
| crep-flights | 8206 | Flights | Aviation data |
| crep-cache-warmer | - | Cache Warmer | Data preloader |

---

## 📋 Complete File Manifest

### WEBSITE Repository - Key Files

#### Core Configuration

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Main Docker Compose for website |
| `docker-compose.crep.yml` | CREP collectors stack |
| `docker-compose.services.yml` | Additional services |
| `Dockerfile.production` | Production Next.js build |
| `.env.local` | Environment variables |

#### CREP Dashboard

| File | Purpose |
|------|---------|
| `app/dashboard/crep/page.tsx` | Main CREP dashboard page |
| `components/crep/*.tsx` | CREP React components |
| `lib/oei/*.ts` | OEI library (connectors, cache, logging) |
| `app/api/oei/*.ts` | OEI API routes |
| `app/api/crep/*.ts` | CREP API routes |

#### OEI Library (Updated 2026-01-16)

| File | Purpose | Lines |
|------|---------|-------|
| `lib/oei/index.ts` | Main exports | 100 |
| `lib/oei/event-bus.ts` | Event bus | 385 |
| `lib/oei/cache-manager.ts` | Multi-layer cache | 250 |
| `lib/oei/snapshot-store.ts` | IndexedDB persistence | 200 |
| `lib/oei/failover-service.ts` | Circuit breaker | 180 |
| `lib/oei/mindex-logger.ts` | MINDEX logging | 288 |
| `lib/oei/connectors/*.ts` | API connectors | ~1500 |

#### CREP Collectors (NEW)

| File | Purpose |
|------|---------|
| `services/crep-collectors/base_collector.py` | Base collector class |
| `services/crep-collectors/carbon_mapper_collector.py` | Carbon Mapper |
| `services/crep-collectors/railway_collector.py` | Railway |
| `services/crep-collectors/astria_collector.py` | Space debris |
| `services/crep-collectors/satmap_collector.py` | Satellites |
| `services/crep-collectors/marine_collector.py` | Marine traffic |
| `services/crep-collectors/flights_collector.py` | Flights |
| `services/crep-collectors/cache_warmer.py` | Cache preloader |
| `services/crep-collectors/requirements.txt` | Python deps |
| `services/crep-collectors/Dockerfile.*` | Docker images |

### MAS Repository - Key Files

#### Core Configuration

| File | Purpose |
|------|---------|
| `docker-compose.yml` | MAS services |
| `docker-compose.always-on.yml` | Always-on stack |
| `config.yaml` | Main configuration |

#### N8n Workflows

| Directory | Purpose |
|-----------|---------|
| `n8n/workflows/` | Workflow definitions |
| `n8n/credentials/` | Credential configurations |

#### Orchestrator

| Directory | Purpose |
|-----------|---------|
| `orchestrator-myca/` | MYCA orchestrator service |
| `agents/` | Agent definitions |
| `services/` | Service configurations |

---

## 🔧 Environment Variables

### Required for WEBSITE

```bash
# Database
POSTGRES_URL=postgresql://mycosoft:password@localhost:5432/mycosoft
POSTGRES_PASSWORD=your_secure_password

# Cache
REDIS_URL=redis://localhost:6379

# MINDEX
MINDEX_API_URL=http://mindex:8000
MINDEX_API_KEY=your_mindex_key

# Authentication
NEXTAUTH_SECRET=your_secret
NEXTAUTH_URL=http://localhost:3000

# Google APIs
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_key
GOOGLE_EARTH_ENGINE_PRIVATE_KEY=your_key

# External APIs (optional but recommended)
OPENSKY_USERNAME=
OPENSKY_PASSWORD=
AISSTREAM_API_KEY=
FLIGHTRADAR24_API_KEY=
MARINETRAFFIC_API_KEY=
CARBON_MAPPER_API_KEY=
```

### Required for MAS

```bash
# Orchestrator
ORCHESTRATOR_PORT=8001
ORCHESTRATOR_HOST=0.0.0.0

# Ollama
OLLAMA_HOST=http://ollama:11434

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# N8n
N8N_HOST=n8n
N8N_PORT=5678
N8N_WEBHOOK_URL=http://n8n:5678

# Voice
WHISPER_HOST=whisper
TTS_HOST=piper-tts
SPEECH_HOST=openedai-speech
```

---

## 🚀 Deployment Steps

### Step 1: Prepare Server

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install docker-compose-plugin

# Create Docker network
docker network create mycosoft-network

# Create data directories
mkdir -p /opt/mycosoft/data/{postgres,redis,qdrant,n8n}
```

### Step 2: Clone Repositories

```bash
cd /opt/mycosoft
git clone https://github.com/mycosoft/website.git website
git clone https://github.com/mycosoft/mycosoft-mas.git mas
```

### Step 3: Configure Environment

```bash
# Copy and configure environment files
cp website/.env.example website/.env.local
cp mas/.env.example mas/.env

# Edit with production values
nano website/.env.local
nano mas/.env
```

### Step 4: Start Core Services

```bash
# Start WEBSITE (includes CREP dashboard)
cd /opt/mycosoft/website
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:3000/api/health
```

### Step 5: Start MAS Services

```bash
# Start MAS stack
cd /opt/mycosoft/mas
docker-compose -f docker-compose.always-on.yml up -d
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8001/health
```

### Step 6: Start CREP Collectors

```bash
cd /opt/mycosoft/website
docker-compose -f docker-compose.crep.yml up -d

# Verify
docker-compose -f docker-compose.crep.yml ps
```

### Step 7: Verify All Services

```bash
# Website
curl http://localhost:3000/api/health

# CREP APIs
curl http://localhost:3000/api/oei/satellites?limit=5
curl http://localhost:3000/api/crep/fungal?limit=5
curl http://localhost:3000/api/oei/opensky?limit=5

# MAS
curl http://localhost:8001/health

# MINDEX
curl http://localhost:8000/api/health

# N8n
curl http://localhost:5678/healthz
```

---

## 📊 Health Monitoring

### Health Check Endpoints

| Service | Endpoint |
|---------|----------|
| Website | `http://localhost:3000/api/health` |
| MAS Orchestrator | `http://localhost:8001/health` |
| MINDEX | `http://localhost:8000/api/health` |
| MycoBrain | `http://localhost:8003/health` |
| N8n | `http://localhost:5678/healthz` |
| Grafana | `http://localhost:3002/api/health` |
| Prometheus | `http://localhost:9090/-/healthy` |

### Dashboard URLs

| Dashboard | URL |
|-----------|-----|
| CREP | http://localhost:3000/dashboard/crep |
| NatureOS | http://localhost:3000/natureos |
| Earth Simulator | http://localhost:3000/apps/earth-simulator |
| Devices | http://localhost:3000/devices |
| MYCA | http://localhost:3100 |
| Grafana | http://localhost:3002 |
| N8n | http://localhost:5678 |

---

## 📚 Documentation Reference

### WEBSITE Repository Docs

| Document | Path | Description |
|----------|------|-------------|
| **CREP Deployment** | `docs/CREP_INFRASTRUCTURE_DEPLOYMENT.md` | Complete CREP setup |
| **CREP Changes** | `docs/CREP_CHANGES_MANIFEST.md` | File changes manifest |
| **OEI Status** | `docs/NATUREOS_OEI_STATUS_AND_ROADMAP.md` | OEI architecture |
| **Port Assignments** | `docs/PORT_ASSIGNMENTS.md` | Port reference |
| **System Architecture** | `docs/SYSTEM_ARCHITECTURE.md` | Overall architecture |
| **Docker Strategy** | `docs/DOCKER_CONTAINERIZATION_STRATEGY.md` | Docker design |

### MAS Repository Docs

| Document | Path | Description |
|----------|------|-------------|
| **CREP Reference** | `docs/CREP_WEBSITE_DEPLOYMENT_REFERENCE.md` | Cross-reference to WEBSITE |
| **This Guide** | `docs/SERVER_MIGRATION_MASTER_GUIDE.md` | Master migration guide |
| **MyCoBrain Status** | `MYCOBRAIN_STATUS_FINAL.md` | MyCoBrain integration |
| **N8n Setup** | `n8n/README_START_HERE.md` | N8n configuration |

---

## ⚠️ Critical Notes

### 1. Repository Separation

- **WEBSITE** repository contains the main application and CREP dashboard
- **MAS** repository contains orchestration and supporting services
- DO NOT mix configurations between repositories

### 2. Network Configuration

- All containers must be on `mycosoft-network` bridge network
- Internal service communication uses container names, not localhost
- External access uses published ports

### 3. Database Persistence

- PostgreSQL data: `/opt/mycosoft/data/postgres`
- Redis data: `/opt/mycosoft/data/redis`
- Qdrant data: `/opt/mycosoft/data/qdrant`
- N8n data: `/opt/mycosoft/data/n8n`

### 4. Backup Strategy

```bash
# Backup PostgreSQL
docker exec mycosoft-postgres pg_dump -U mycosoft mycosoft > backup.sql

# Backup Redis
docker exec mycosoft-redis redis-cli BGSAVE

# Backup volumes
docker run --rm -v mycosoft_data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz /data
```

### 5. Rebuild After Changes

```bash
# Rebuild website
cd /opt/mycosoft/website
docker-compose build website --no-cache
docker-compose up -d website

# Clear browser cache
# Navigate to http://localhost:3000/dashboard/crep
```

---

## 🔄 Recent Changes (2026-01-16)

### CREP Infrastructure Enhancement

- ✅ Fixed layer toggles (aviation, ships, satellites now enabled by default)
- ✅ Added MINDEX logging to all API routes
- ✅ Created multi-layer cache system
- ✅ Created failover service with circuit breaker
- ✅ Created 6 new CREP collector containers
- ✅ Fixed Dockerfile.production (npm instead of pnpm)
- ✅ Verified 21,757+ fungal observations from MINDEX
- ✅ Created comprehensive documentation

### Files Modified

- `app/dashboard/crep/page.tsx` - Enabled layers
- `Dockerfile.production` - npm fix
- `app/api/oei/*.ts` - MINDEX logging
- `app/api/crep/fungal/route.ts` - MINDEX logging
- `lib/oei/index.ts` - New exports

### Files Created

- `lib/oei/cache-manager.ts`
- `lib/oei/snapshot-store.ts`
- `lib/oei/failover-service.ts`
- `lib/oei/mindex-logger.ts`
- `docker-compose.crep.yml`
- `services/crep-collectors/*`

---

## ✅ Pre-Flight Checklist

Before deploying to production:

- [ ] All environment variables configured
- [ ] Docker network created
- [ ] Data directories exist with proper permissions
- [ ] PostgreSQL connection tested
- [ ] Redis connection tested
- [ ] MINDEX API accessible
- [ ] Website builds successfully
- [ ] CREP dashboard loads
- [ ] All API routes return data
- [ ] Monitoring dashboards accessible
- [ ] Backups configured

---

*This is the authoritative server migration guide. Generated 2026-01-16.*
