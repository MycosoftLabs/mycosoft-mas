# MYCA Presence

**Component**: Live user presence, sessions, online status, API usage  
**Status**: Implemented (Feb 24, 2026)

## Overview

MYCA has real-time awareness of:
- Who is logged in (staff, superusers, regular users)
- Active sessions and current page
- API activity and data intake/usage

## Locations

### Website

| File | Purpose |
|------|---------|
| `hooks/usePresenceHeartbeat.ts` | 30s heartbeat, session lifecycle |
| `contexts/presence-context.tsx` | PresenceProvider, enables heartbeat when logged in |
| `lib/api-usage-interceptor.ts` | Tracks API calls for data intake |
| `app/api/presence/heartbeat/route.ts` | POST heartbeat |
| `app/api/presence/sessions/route.ts` | GET active sessions |
| `app/api/presence/online/route.ts` | GET online users |
| `app/api/presence/stream/route.ts` | SSE real-time presence |
| `app/api/presence/api-usage/route.ts` | API usage logs |

### MAS

| File | Purpose |
|------|---------|
| `consciousness/sensors.py` | PresenceSensor reads from website API |
| `core/routers/presence_api.py` | /api/presence/online, /sessions, /staff, /stats, /stream |
| `consciousness/world_model.py` | Presence in world state (5s update) |
| `consciousness/deliberation.py` | Presence in deliberation context |
| `consciousness/attention.py` | Presence keywords in attention |

### Supabase

| Table | Purpose |
|-------|---------|
| `active_sessions` | Session lifecycle, page_path, metadata |
| `user_heartbeat` | Heartbeats, current_page, activity_type |
| `api_usage_log` | Endpoint, method, status_code, response_time |
| `is_staff()` | RLS helper for staff role |

## Auth

- **Heartbeat**: Requires authenticated user (Supabase auth).
- **Sessions/Online**: Auth or `x-service-key: PRESENCE_SERVICE_KEY` (service-to-service).
- **Staff view**: `profiles.role` in (admin, superuser, owner, staff).

## Environment

- `PRESENCE_API_URL` – Website presence API (default http://192.168.0.187:3000/api/presence)
- `PRESENCE_SERVICE_KEY` – Service key for MAS→website

## Used By

- MYCA consciousness (world model, deliberation, attention)
- Staff dashboards (future)
- Superuser training feedback (orchestrator)
