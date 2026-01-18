# CREP Website Deployment Reference

**Date**: 2026-01-16  
**Status**: PRODUCTION READY  
**Target Repository**: WEBSITE (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\`)

---

## ⚠️ IMPORTANT: Repository Location

The CREP dashboard is in the **WEBSITE** repository, NOT the MAS repository.

| System | Repository | Port | Status |
|--------|------------|------|--------|
| **CREP Dashboard** | WEBSITE | 3000 | ✅ ACTIVE |
| ~~MAS Dashboard~~ | ~~MAS~~ | ~~3001~~ | ❌ DEPRECATED |

---

## Quick Reference

### CREP Dashboard URL

```
http://localhost:3000/dashboard/crep
```

### Key Documentation (in WEBSITE repo)

| Document | Path |
|----------|------|
| **Deployment Guide** | `docs/CREP_INFRASTRUCTURE_DEPLOYMENT.md` |
| **Session Summary** | `docs/SESSION_SUMMARY_JAN16_2026_CREP_INFRASTRUCTURE.md` |
| **Changes Manifest** | `docs/CREP_CHANGES_MANIFEST.md` |
| **OEI Status** | `docs/NATUREOS_OEI_STATUS_AND_ROADMAP.md` |
| **Port Assignments** | `docs/PORT_ASSIGNMENTS.md` |
| **System Architecture** | `docs/SYSTEM_ARCHITECTURE.md` |

---

## Deployment Commands

### From WEBSITE Directory

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website

# Build and start website
docker-compose build website --no-cache
docker-compose up -d website

# Start CREP collectors
docker-compose -f docker-compose.crep.yml up -d

# Verify
curl http://localhost:3000/api/health
```

---

## Files Modified on 2026-01-16

### Core Changes

| File | Type | Description |
|------|------|-------------|
| `app/dashboard/crep/page.tsx` | Modified | Enabled infrastructure layers by default |
| `Dockerfile.production` | Modified | Changed from pnpm to npm |
| `app/api/oei/opensky/route.ts` | Modified | Added MINDEX logging |
| `app/api/oei/flightradar24/route.ts` | Modified | Added MINDEX logging |
| `app/api/oei/aisstream/route.ts` | Modified | Added MINDEX logging |
| `app/api/oei/satellites/route.ts` | Modified | Added MINDEX logging |
| `app/api/crep/fungal/route.ts` | Modified | Added MINDEX logging |

### New Files

| File | Description |
|------|-------------|
| `lib/oei/cache-manager.ts` | Multi-layer cache system |
| `lib/oei/snapshot-store.ts` | IndexedDB persistence |
| `lib/oei/failover-service.ts` | Circuit breaker pattern |
| `lib/oei/mindex-logger.ts` | MINDEX logging service |
| `docker-compose.crep.yml` | 6 new data collector containers |
| `services/crep-collectors/*` | Python collector services |

---

## Docker Container Architecture

### Main Stack (docker-compose.yml)

| Container | Port | Service |
|-----------|------|---------|
| mycosoft-website | 3000 | Next.js website |
| mycosoft-postgres | 5432 | PostgreSQL database |
| mycosoft-redis | 6379 | Redis cache |

### CREP Collectors (docker-compose.crep.yml)

| Container | Port | Service |
|-----------|------|---------|
| crep-carbon-mapper | 8201 | Carbon Mapper data |
| crep-railway | 8202 | Railway infrastructure |
| crep-astria | 8203 | Space debris tracking |
| crep-satmap | 8204 | Enhanced satellites |
| crep-marine | 8205 | Marine traffic |
| crep-flights | 8206 | Enhanced flights |
| crep-cache-warmer | - | Cache preloader |

---

## API Routes

| Route | Description | Logged to MINDEX |
|-------|-------------|------------------|
| `/api/oei/opensky` | Aircraft from OpenSky | ✅ Yes |
| `/api/oei/flightradar24` | Flights from FR24 | ✅ Yes |
| `/api/oei/aisstream` | Vessels from AISstream | ✅ Yes |
| `/api/oei/satellites` | Satellites from CelesTrak | ✅ Yes |
| `/api/crep/fungal` | Fungi from MINDEX | ✅ Yes |

---

## Environment Variables Required

```bash
# Database
POSTGRES_URL=postgresql://mycosoft:password@localhost:5432/mycosoft
POSTGRES_PASSWORD=secure_password

# Cache
REDIS_URL=redis://localhost:6379

# MINDEX
MINDEX_API_URL=http://localhost:8000
MINDEX_API_KEY=your_key

# External APIs (optional)
OPENSKY_USERNAME=
OPENSKY_PASSWORD=
AISSTREAM_API_KEY=
FLIGHTRADAR24_API_KEY=
```

---

## Health Verification

```powershell
# Test website
curl http://localhost:3000/api/health

# Test CREP APIs
curl http://localhost:3000/api/oei/satellites?limit=5
curl http://localhost:3000/api/crep/fungal?limit=5
curl http://localhost:3000/api/oei/opensky?limit=5

# Check containers
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## Cross-Reference: MAS Repository

The MAS repository contains:
- `docker-compose.always-on.yml` - References mycosoft-website
- `docker-compose.yml` - MAS-specific services (orchestrator, n8n, etc.)

**Note**: The website source code is NOT in the MAS repository. Always deploy from the WEBSITE repository.

---

*This is a reference document pointing to the WEBSITE repository where the CREP dashboard lives.*
