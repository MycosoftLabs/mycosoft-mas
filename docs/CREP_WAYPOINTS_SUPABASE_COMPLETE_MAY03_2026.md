# CREP Waypoints — Supabase Source of Truth Complete (May 03, 2026)

**Date:** May 03, 2026  
**Status:** Complete (schema + API + client sync)  
**Related:** `docs/MAY02_CONTINUATION_ROLLOUT_COMPLETE_MAY02_2026.md` follow-up closure

## Schema

| Migration | Purpose |
|-----------|---------|
| `WEBSITE/website/supabase/migrations/20260502_natureos_crep_waypoints.sql` | Base table `crep_waypoints` with RLS policies per `user_id`. |
| `WEBSITE/website/supabase/migrations/20260503_natureos_crep_waypoints_attrs.sql` | `payload jsonb`, `client_legacy_id` + unique index for idempotent migration from local ids (`wp-*`). |

## API

- `app/api/crep/waypoints/route.ts` — list/create (authenticated Supabase server client).
- `app/api/crep/waypoints/[id]/route.ts` — get/update/delete own rows only.

## Client

- `components/crep/waypoints/WaypointSystem.tsx` — when signed in: load from Supabase; one-time merge from `localStorage` (`crep.waypoints.v1`) with upsert + migration marker; saves go **server-first**; offline/session-missing behavior uses cache only as fallback.

## Ops

Apply both migrations in the Supabase project; enable Realtime on `crep_waypoints` only if product requires live collaboration.
