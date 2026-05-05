# Agaric Device Page + Device Tracker — Complete — May 03, 2026

**Date:** May 3, 2026  
**Status:** Complete (localhost verification; deploy out of scope for this pass)  
**Plan:** Agaric device + registry (user-approved scope)  
**Related:** `docs/DEVICES_REGISTRY_MAY03_2026.md`, `.cursor/agents/device-tracker.md`

## Delivered

1. **Website** — `/devices/agaric` (App Router) with `AgaricDetails` neuromorphic page mirroring Mushroom 1 structure: hero, mission, carousel, variant tabs, blueprint hotspots, payload table, mesh section, use cases, competitive table, CTAs. Asset paths under `/assets/agaric/*` with existing video fallback helpers (no mock telemetry).
2. **Portal + nav** — Agaric card in `components/devices/devices-portal.tsx`; `Plane` icon entries in `components/header.tsx` and `components/mobile-nav.tsx` (Psathyrella restored to mobile list for parity with header where applicable).
3. **Earth Simulator API** — `app/api/earth-simulator/devices/route.ts` merges `KNOWN_DEVICE_CATALOG` from `lib/devices/catalog.ts` with live `GET {MYCOBRAIN_SERVICE_URL|MYCOBRAIN_API_URL}/devices` (default `http://localhost:8003`). Rows tagged `source: "catalog" | "live"`.
4. **MAS** — `device_registry_api.py` `device_role` Field description extended with `myconode`, `psathyrella`, `agaric_mini`, `agaric_standard`, `agaric_heavy`, and `mycodrone` generic.
5. **NatureOS Device Registry** — Read-only “known device types” strip on `/natureos/devices/registry` sourced from the same catalog (types without MAS heartbeats still visible to ops).
6. **Subagent** — `device-tracker` in `MAS/mycosoft-mas/.cursor/agents/` and `WEBSITE/website/.cursor/agents/`.
7. **Docs** — This file + `DEVICES_REGISTRY_MAY03_2026.md` + registry index updates.

## Files touched (summary)

| Repo | Path |
|------|------|
| website | `app/devices/agaric/page.tsx` |
| website | `components/devices/agaric-details.tsx` |
| website | `components/devices/devices-portal.tsx` |
| website | `components/header.tsx` |
| website | `components/mobile-nav.tsx` |
| website | `lib/devices/catalog.ts` |
| website | `app/api/earth-simulator/devices/route.ts` |
| website | `app/natureos/devices/registry/page.tsx` |
| MAS | `mycosoft_mas/core/routers/device_registry_api.py` |
| MAS + website | `.cursor/agents/device-tracker.md` |
| MAS | `docs/DEVICES_REGISTRY_MAY03_2026.md`, `docs/AGARIC_DEVICE_AND_DEVICE_TRACKER_MAY03_2026.md` |
| MAS | `docs/MASTER_DOCUMENT_INDEX.md`, `.cursor/CURSOR_DOCS_INDEX.md`, `docs/SYSTEM_REGISTRY_FEB04_2026.md` |

## How to verify

1. From `WEBSITE/website`: `npm run dev:next-only` (port **3010**, external process per project rules).
2. Open `http://localhost:3010/devices` — Agaric card present; navigate to `http://localhost:3010/devices/agaric` — page renders (videos may show poster if files missing).
3. `Invoke-RestMethod http://localhost:3010/api/earth-simulator/devices` — JSON includes `agaric-mini`, `agaric-standard`, `agaric-heavy` with `source: "catalog"` when MycoBrain is offline.
4. `http://localhost:3010/natureos/devices/registry` — “Known device types” list includes Agaric variants and links.

## Morgan follow-up (assets)

Upload imagery and video to NAS path **`\\192.168.0.105\mycosoft.com\website\assets\agaric\`** matching paths referenced in `agaric-details.tsx` / `AGARIC_ASSETS` (e.g. `hero.mp4`, `1.jpg` …). Sandbox container must keep NAS read-only mount per ops runbook.

## Deploy

See **`docs/AGARIC_DEVICE_REGISTRY_DEPLOY_HANDOFF_MAY04_2026.md`** for the full checklist another agent should execute (Sandbox 187 + MAS 188 + Cloudflare + optional Cursor sync).
