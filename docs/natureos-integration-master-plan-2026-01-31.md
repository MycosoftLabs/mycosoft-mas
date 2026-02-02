# 2026-01-31 NatureOS Integration Master Plan (Website, MINDEX, MAS, MycoBrain)

## Purpose
Define the integration work required to make NatureOS a full operating system for nature
by aligning the website, MINDEX, Mycosoft-MAS (including PersonaPlex), and MycoBrain.
This plan avoids mock data and requires real telemetry, real datasets, and verified
service connections.

## Documents reviewed (latest first)
### Mycosoft-MAS (PersonaPlex + orchestration)
- 2026-01-29: PERSONAPLEX_DEPLOYMENT_JAN29_2026.md
- 2026-01-29: PERSONAPLEX_INTEGRATION_COMPLETE_JAN29_2026.md
- 2026-01-29: PERSONAPLEX_COMPLETE_SETUP_JAN29_2026.md
- 2026-01-29: PERSONAPLEX_NATIVE_FIX_JAN29_2026.md
- 2026-01-29: PERSONAPLEX_WORKING_JAN29_2026.md
- 2026-01-29: VOICE_FULL_DUPLEX_WORKING_JAN29_2026.md
- 2026-01-29: VOICE_SYSTEM_FIX_JAN29_2026.md
- 2026-01-28: PERSONAPLEX_LOCAL_TESTING_JAN28_2026.md
- 2026-01-28: NETWORK_RECOVERY_COMPLETE_JAN28_2026.md
- 2026-01-28: NETWORK_STATUS_JAN28_2026.md
- 2026-01-28: PROXMOX_PASSWORD_RESET_GUIDE.md

### NatureOS (this repo)
- 2026-01-31: earth-2-personaplex-integration-report-2026-01-31.md

## Current integration anchors
1. NatureOS Core API provides device management, event ingest, and MycoBrain telemetry.
2. MINDEX (Cosmos DB) stores events, devices, and telemetry.
3. MAS provides orchestration, agent execution, and PersonaPlex full-duplex voice.
4. Website provides dashboards and UI integrations.

## Key integration gaps (must be closed)
1. **API contract mismatch (MAS ↔ NatureOS)**
   - MAS `NATUREOSClient` expects `/devices`, `/devices/register`,
     `/devices/{id}/sensor-data`, and `/devices/{id}/commands/mycobrain`.
   - NatureOS currently exposes `/api/devices` and `/api/mycobrain/*`.
2. **Mock data in NatureOS responses**
   - Randomized and placeholder outputs must be removed to comply with real data only.
3. **PersonaPlex routing into NatureOS workflows**
   - PersonaPlex already routes to MAS orchestrator but NatureOS needs API endpoints
     and task handlers for real-world actions.
4. **Unified telemetry and device schemas**
   - MycoBrain telemetry needs to be surfaced as generic sensor readings for
     MAS and Website without lossy conversions.
5. **Evidence and provenance**
   - All data sent to MAS or website must include source, timestamp, and quality metadata.

## Integration work streams
### Stream A: API compatibility (MAS ↔ NatureOS)
- Add compatibility routes in NatureOS to satisfy MAS `NATUREOSClient` expectations.
- Ensure endpoints return real data from MINDEX (no placeholders).
- Map MycoBrain command requests to actual MDP commands (no fake sequences).

### Stream B: Remove mock data from NatureOS
- Eliminate randomized metrics and placeholder classifications.
- Replace with real metrics when available or report "unavailable" explicitly.

### Stream C: PersonaPlex-driven operations
- Route PersonaPlex intents → MAS → NatureOS actions:
  - Device control (MycoBrain commands)
  - Data queries (events, devices, telemetry)
  - Earth-2 / CREP / Earth Simulator actions (via MAS tools)

### Stream D: MINDEX + Website alignment
- Ensure Website dashboards use real MINDEX data and telemetry.
- Provide consistent schemas for devices, events, and spore/track data.

## Required NatureOS implementation tasks
1. **Compatibility Controller**
   - `GET /devices`
   - `GET /devices/{deviceId}`
   - `POST /devices/register`
   - `PUT /devices/{deviceId}/config` (metadata-based config updates)
   - `GET /devices/{deviceId}/sensor-data`
   - `POST /devices/{deviceId}/commands/mycobrain`
2. **Telemetry Mapping**
   - Map MycoBrain BME688 telemetry to generic sensor readings:
     temperature, humidity, pressure, gas_resistance.
3. **Real health metrics**
   - Replace simulated CPU/Memory/Disk metrics with real OS readings.
   - Use configuration-only checks where live connectivity checks are not possible.
4. **Fungal classification**
   - Remove placeholder taxonomy and morphology outputs.
   - Return null/unknown when no real model is available.

## Required MAS implementation tasks (tracked in MAS repo)
1. Expand PersonaPlex tool registry to include NatureOS commands:
   - device status, telemetry queries, command dispatch.
2. Add NatureOS adapters for CREP/Earth Simulator actions.
3. Ensure MAS task routing targets NatureOS endpoints (not mock data).

## Definition of done
- MAS can call NatureOS endpoints using its existing client without errors.
- Website and MAS dashboards show real device and telemetry data only.
- NatureOS returns no randomized or placeholder values.
- PersonaPlex can trigger real workflows through MAS and NatureOS.

## Open inputs needed
- Confirm which NatureOS endpoints MAS should prefer long-term (compat vs /api).
- Confirm which telemetry fields are canonical for generic sensor data.
- Confirm MAS task schemas for device commands and data queries.
