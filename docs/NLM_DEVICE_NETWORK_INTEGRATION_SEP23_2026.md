# NLM Device Network Integration — SEP23 2026

**Date:** September 23, 2026  
**Status:** Complete (device↔NLM wire; no 187 cutover)  
**Related:** `WEBSITE/website/docs/FORMSPACE_NLM_FULL_BUILD_PLAN_SEP23_2026.md`

## Root cause

NLM ingest/training was **disconnected from the real device network**:

1. **`/api/natureos/nlm-training/ingest/live`** fan-out probed many dead paths (`/api/devices/network` on MAS, health-only, etc.) with serial 3s timeouts → request often **timed out** before returning MAS registry devices.
2. When MAS heartbeats were found, gateways reported **`sensors: []`** (service waiting for ESP32). NLM never enriched from **field MDP maps** / role sensor catalogs or pulled **`/api/devices/{id}/telemetry`**.
3. **Training runs** (Supabase + MAS `/api/nlm/training/start`) had **no `device_id` / `sensor_id` fields**, so ingest could not ground training on real sensors.
4. UI showed a thin device list with **no sensor_id rows**, **no link to `/natureos/devices/network`**, and **no bind-to-training** action.

MycoBrain `:8003`, MAS registry heartbeats, website `/api/devices/network`, and MDP path resolution already existed — NLM simply did not join them.

## What was wired

| Layer | Change |
|-------|--------|
| Website lib | `lib/nlm/device-stream-bridge.ts` — MAS registry + MycoBrain + field map → devices/sensors with `device_id` + `sensor_id`; samples null when offline |
| Website BFF | `ingest/live` rewritten; `ingest/bind` validates bindings → MAS; `runs` stores `device_bindings` / `device_ids` / `sensor_ids` in metrics |
| MAS | `StartTrainingRequest` + run config carry bindings; `GET /api/nlm/training/ingest/sources`; `POST /api/nlm/training/ingest/bind` |
| UI | `IngestionConsole` — per-sensor checklist, network map links, bind button; `TrainingRunDetail` — bindings panel |
| Hooks | `useLiveIngest` returns `sensors`, `networkMapHref`, `note` |

**No mock samples.** Declared role sensors appear as `status: declared` / `sample: null` until MDP telemetry exists.

**Deploy freeze:** no nginx cutover on 187.

## How to verify with real devices

1. Ensure a MycoBrain service heartbeats to MAS (`http://192.168.0.188:8001/api/devices`) and/or an ESP32 appears under MycoBrain `/devices`.
2. Local website: `GET http://localhost:3010/api/natureos/nlm-training/ingest/live`  
   - Expect `devices[]` with `device_id`, `sensors[].sensor_id`, `network_href`.  
   - Online MDP telemetry → non-null `sample`; offline → `sample: null`.
3. Open `/myca/nlm` → Ingest → select sensors → **Bind to training** (owner auth).
4. `POST /api/natureos/nlm-training/runs` with `deviceBindings: [{device_id, sensor_id}]` — run metrics must include bindings.
5. MAS (after code deploy to 188): `GET /api/nlm/training/ingest/sources`, `POST /api/nlm/training/ingest/bind`.
6. Device network UI: `/natureos/devices/network?device=<device_id>` matches NLM map links.

## Follow-ups (not this task)

- Durable NAS/SQL training lineage + Merkle per-frame from live sensors
- Mycorrhizae `:8002` channel merge when that API is reachable
- Deploy MAS router to 188 when freeze lifts
