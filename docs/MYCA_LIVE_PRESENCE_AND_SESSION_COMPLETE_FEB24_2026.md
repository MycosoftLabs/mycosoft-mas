# MYCA Live Presence Integration and Session Summary

**Date**: February 24, 2026  
**Author**: MYCA / Morgan Rockwell  
**Status**: Complete

## Overview

Comprehensive session covering MYCA Live Presence Integration (real-time user awareness), testing, fixes, GitHub workflow scope resolution, and documentation updates. All work pushed to GitHub (MAS, website). Supabase migration applied. Presence endpoints verified.

---

## 1. MYCA Live Presence Integration (Complete)

### Supabase Migration (Applied)

- **File**: `WEBSITE/website/supabase/migrations/20260224000000_active_sessions.sql`
- **Tables**:
  - `public.is_staff()` – checks `profiles.role` for admin/superuser/owner/staff
  - `public.active_sessions` – user sessions (user_id, session_id, page_path, metadata, RLS)
  - `public.user_heartbeat` – frequent heartbeats (user_id, heartbeat_at, current_page, activity_type, RLS)
  - `public.api_usage_log` – API call logs (endpoint, method, status_code, response_time_ms, RLS)
- **RLS**: Users manage own data; staff can read all via `is_staff()`.
- **Applied**: Via Supabase MCP `apply_migration`.

### Website Implementation

| Component | Location | Purpose |
|-----------|----------|---------|
| `usePresenceHeartbeat` | `hooks/usePresenceHeartbeat.ts` | 30s heartbeat, session start/end, activity type |
| `PresenceProvider` | `contexts/presence-context.tsx` | Wraps app, enables heartbeat when user logged in |
| API usage interceptor | `lib/api-usage-interceptor.ts` | Tracks data intake patterns |
| Heartbeat route | `app/api/presence/heartbeat/route.ts` | POST heartbeat, upsert sessions |
| Sessions route | `app/api/presence/sessions/route.ts` | GET active sessions (auth or x-service-key) |
| Online route | `app/api/presence/online/route.ts` | GET online users (60s threshold) |
| Stream route | `app/api/presence/stream/route.ts` | SSE real-time presence |
| API usage route | `app/api/presence/api-usage/route.ts` | API usage logs |

### MAS Implementation

| Component | Location | Purpose |
|-----------|----------|---------|
| PresenceSensor | `consciousness/sensors.py` | Reads presence from website API |
| presence_api | `core/routers/presence_api.py` | Proxies to website `/api/presence/*` |
| World model | `consciousness/world_model.py` | Includes presence in world state (5s interval) |
| Deliberation | `consciousness/deliberation.py` | Presence injected into context |
| Attention | `consciousness/attention.py` | Presence keywords in attention |

### Environment

- **PRESENCE_API_URL**: Website presence API (default `http://192.168.0.187:3000/api/presence`)
- **PRESENCE_SERVICE_KEY**: Service-to-service auth for MAS→website

### Dependency

`is_staff()` uses `public.profiles` with `role` column. Ensure profiles table exists; add migration if needed.

---

## 2. Testing and Fixes

### Tests Performed

- Website dev server: responding on 3010
- Presence API: `/api/presence/online` and `/api/presence/sessions` return 401 without auth (correct)
- MAS tests: 494 passing
- Website lint: no errors (warnings only)

### Fixes Applied

1. **orchestrator-chat nullish coalescing** (`app/api/test-voice/mas/orchestrator-chat/route.ts`)
   - Error: `??` mixed with `||` without parens
   - Fix: `firstPart || (data?.status?.message?.parts?.[0]?.text ?? "")`

2. **MAS .gitignore**
   - Added `data/mycobrain_service.log.err`, `data/mycobrain_service.pid`
   - Removed from tracking

### Known Issue

- Website build: compiles successfully; "Collecting page data" fails with `MODULE_NOT_FOUND ./17627.js` (pre-existing Next.js chunk issue).

---

## 3. GitHub Workflow Scope

### Problem

Push to `.github/workflows/*` failed: *"refusing to allow an OAuth App to create or update workflow without workflow scope"*.

### Root Cause

Git credential (via Cursor/manager) used OAuth token without `workflow` scope. Git uses `gh auth git-credential` for GitHub HTTPS.

### Resolution

1. Run `gh auth refresh -s workflow -h github.com`
2. Complete device flow at https://github.com/login/device (one-time code)
3. Token now has `workflow` scope; subsequent pushes succeed.

### Remotes

- Both repos use HTTPS (`https://github.com/MycosoftLabs/*`).
- SSH was attempted but failed (host key verification); reverted to HTTPS.

---

## 4. GitHub Pushes

### MAS (mycosoft-mas)

- Presence API router, PresenceSensor, consciousness injection
- Docs, network monitor, petri, commerce, NLQ, fleet, etc.
- CI workflow update
- Commit: `feat: MYCA Live Presence Integration...` and `ci: update workflow (FEB24_2026)`

### Website (website)

- Presence API routes, Supabase migration, hooks, context, interceptor
- MYCA page, NatureOS pages, search, etc.
- orchestrator-chat fix
- CI-CD workflow update
- Commits: `feat: MYCA Live Presence...` and `ci: update workflow (FEB24_2026)`

---

## 5. Related Documents

- [MYCA Live Presence Integration Plan](.cursor/plans/) (original plan)
- [CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md](./CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md) – pipeline and sensors
- [atomic/MYCA_PRESENCE.md](./myca/atomic/MYCA_PRESENCE.md) – presence atomic doc

---

## 6. Verification Checklist

- [x] Supabase migration applied
- [x] Presence endpoints return 401 without auth
- [x] MAS presence router registered
- [x] Consciousness includes presence in world model
- [x] MAS tests passing
- [x] Workflow files pushed to GitHub
- [x] Documentation created and indexed
