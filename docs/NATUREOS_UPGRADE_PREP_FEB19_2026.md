# NatureOS Upgrade Prep and Dashboard Fix

**Date**: February 19, 2026
**Status**: Complete (Fix Applied) / Ready for Upgrade
**Related**: `natureos-integration-master-plan-2026-01-31.md`, `frontend-integration-guide.md`, `COMPREHENSIVE_SYSTEM_STATUS.md`

## Overview

This document summarizes the NatureOS dashboard fix for `TypeError: Failed to fetch`, consolidates all NatureOS documentation, and outlines the upgrade roadmap for a full NatureOS enhancement.

---

## Fix Applied (Feb 19, 2026)

### Issue
- **Error**: `TypeError: Failed to fetch` in `fetchMindexData` (natureos-dashboard.tsx)
- **Cause**: One failed MINDEX API call caused `Promise.all` to reject, crashing the dashboard
- **Context**: Dashboard fetches `/api/mindex/observations` and `/api/natureos/mindex/stats` on load

### Changes Made

1. **`components/dashboard/natureos-dashboard.tsx`**
   - Switched from `Promise.all` to `Promise.allSettled` so one failing fetch does not break the other
   - Added explicit base URL: `window.location.origin` for robust client-side resolution
   - Added `AbortSignal.timeout(15000)` to avoid indefinite hangs
   - Individual error handling for observations vs stats; console.warn instead of crash

2. **`app/api/mindex/observations/route.ts`**
   - Fixed MINDEX URL: was `host.docker.internal:8001` (MAS port); now uses `MINDEX_API_URL` / `MINDEX_API_BASE_URL` / `192.168.0.189:8000`
   - Correct path for MINDEX API: `/api/mindex/observations`

### Verification
- Dashboard loads without crashing when MINDEX or observations API is slow/unavailable
- Observations and stats populate independently
- Fallback to `liveStats` when MINDEX stats are unavailable

---

## NatureOS Documentation Index

### Core NatureOS Repo (`NATUREOS/NatureOS/`)

| Document | Purpose |
|----------|---------|
| `docs/natureos-integration-master-plan-2026-01-31.md` | Integration work for website, MINDEX, MAS, MycoBrain |
| `docs/frontend-integration-guide.md` | v0.dev frontend → NatureOS backend integration |
| `docs/mycosoft-integration.md` | Ecosystem integration (MINDEX, MYCA, devices, website) |
| `docs/integration-action-plan.md` | Prioritized integration improvements |
| `docs/integration-improvement-plan.md` | Enhancement roadmap |
| `docs/production-readiness-status.md` | Azure deployment, Key Vault, CI/CD status |
| `docs/quick-integration-wins.md` | Fast integration improvements |
| `docs/key-vault-configuration.md` | Key Vault setup |
| `docs/github-secrets-setup.md` | GitHub Actions secrets |
| `docs/earth-2-personaplex-integration-report-2026-01-31.md` | Earth2 + PersonaPlex integration |
| `docs/mycosoft-integration.md` | Full ecosystem integration guide |
| `COMPREHENSIVE_SYSTEM_STATUS.md` | Production readiness, tests, deployment |
| `INTEGRATION_COMPLETE.md` | Integration completion status |
| `COMPLETE_DEPLOYMENT_STATUS.md` | Deployment status |

### Website Integration

| Component | Location | Purpose |
|-----------|----------|---------|
| NatureOS Dashboard | `website/components/dashboard/natureos-dashboard.tsx` | Main dashboard UI |
| NatureOS Page | `website/app/natureos/page.tsx` | Dashboard route |
| MINDEX Observations API | `website/app/api/mindex/observations/route.ts` | iNaturalist + GBIF + MINDEX observations |
| MINDEX Stats API | `website/app/api/natureos/mindex/stats/route.ts` | MINDEX stats proxy |
| Global Events API | `website/app/api/natureos/global-events/route.ts` | Map overlay events |
| NatureOS API Hooks | `website/lib/natureos-api.ts` | useSystemMetrics, useMyceliumNetwork, etc. |

### VM Layout (Reference)

| VM | IP | Role |
|----|-----|------|
| Sandbox | 192.168.0.187 | Website Docker, MycoBrain host |
| MAS | 192.168.0.188 | Orchestrator 8001, n8n 5678, Ollama 11434 |
| MINDEX | 192.168.0.189 | Postgres 5432, Redis 6379, Qdrant 6333, MINDEX API 8000 |
| GPU node | 192.168.0.190 | Voice, Earth2, inference |

---

## Upgrade Roadmap

### Phase 1: API Compatibility (MAS ↔ NatureOS)
- [ ] Add compatibility routes in NatureOS: `/devices`, `/devices/register`, `/devices/{id}/sensor-data`, `/devices/{id}/commands/mycobrain`
- [ ] Replace any mock data with real MINDEX/device data or explicit "unavailable"
- [ ] Map MycoBrain commands to real MDP sequences

### Phase 2: Remove Mock Data
- [ ] Remove randomized metrics and placeholder classifications
- [ ] Return "unavailable" when real data is not available
- [ ] Use live health metrics (CPU/Memory) where possible

### Phase 3: PersonaPlex-Driven Operations
- [ ] Route PersonaPlex intents → MAS → NatureOS
- [ ] Device control via MycoBrain commands
- [ ] Data queries (events, devices, telemetry)
- [ ] Earth-2 / CREP / Earth Simulator actions via MAS tools

### Phase 4: MINDEX + Website Alignment
- [ ] Website dashboards use real MINDEX data only
- [ ] Consistent schemas for devices, events, spore/track data
- [ ] Real-time SignalR / WebSocket for live updates (see frontend-integration-guide.md)

### Phase 5: Real-Time Enhancement
- [ ] Server-Sent Events or SignalR for live dashboard updates
- [ ] Redis caching for API responses
- [ ] MYCA context awareness (active devices, recent events, system health)

---

## Key Integration Gaps (from Master Plan)

1. **API contract mismatch**: MAS `NATUREOSClient` expects `/devices`, etc.; NatureOS exposes `/api/devices`, `/api/mycobrain/*`
2. **Mock data**: Randomized outputs must be removed
3. **PersonaPlex routing**: NatureOS needs API endpoints for real-world actions
4. **Unified telemetry schemas**: MycoBrain telemetry as generic sensor readings
5. **Evidence/provenance**: Source, timestamp, quality metadata for all data

---

## Environment Variables

```bash
# Website .env.local (for dev)
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_API_BASE_URL=http://192.168.0.189:8000
MAS_API_URL=http://192.168.0.188:8001
NEXT_PUBLIC_MAS_API_URL=http://192.168.0.188:8001
```

---

## Quick Test Commands

```bash
# MINDEX health
curl http://192.168.0.189:8000/api/mindex/health

# Website dev server (port 3010)
cd WEBSITE/website && npm run dev:next-only

# NatureOS dashboard
# Open http://localhost:3010/natureos
```

---

## Related Documents

- [VM Layout and Dev Remote Services](../.cursor/rules/vm-layout-and-dev-remote-services.mdc)
- [NatureOS Integration Master Plan](../../NATUREOS/NatureOS/docs/natureos-integration-master-plan-2026-01-31.md)
- [Frontend Integration Guide](../../NATUREOS/NatureOS/docs/frontend-integration-guide.md)
- [Integration Action Plan](../../NATUREOS/NatureOS/docs/integration-action-plan.md)
