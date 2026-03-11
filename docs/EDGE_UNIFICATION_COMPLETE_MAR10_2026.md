# Edge Unification Complete — Jetson/MycoBrain/CREP/MYCA

**Date:** March 10, 2026  
**Status:** Complete  
**Plan:** Mycosoft Full Integration Master Program, Phase 7

---

## Overview

Unified Jetson/MycoBrain runtime, telemetry, CREP presence, and MYCA/AVANI interaction for production edge hardware. Single control plane anchored to MAS; no parallel registries.

---

## Architecture Summary

### Data Flow

```
MycoBrain Service (8003)          Gateway Router (Jetson4)
        │                                  │
        │ heartbeat                        │ heartbeat + telemetry
        ▼                                  ▼
   MAS /api/devices/heartbeat    MAS /api/devices/heartbeat
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
              Device Registry (MAS)
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   CREP (/api/mycobrain)   MYCA (mycobrain_bridge)   Telemetry Ingest
   Device Manager          Device status/telemetry   MINDEX/Supabase
```

### Canonical Contract

- **Heartbeat:** `POST {MAS}/api/devices/heartbeat` (DeviceHeartbeat schema)
- **Telemetry:** `POST {TELEMETRY_INGEST_URL}/api/devices/ingest` or MINDEX `/api/fci/telemetry`
- **Commands:** `POST {MAS}/api/devices/{device_id}/command` — forwards to device or Mycorrhizae
- **CREP:** Website `/api/mycobrain` merges local service + MAS registry; CREP dashboard shows MycoBrain layer
- **MYCA:** `mycobrain_bridge` fetches device status from MAS `/api/devices`

---

## Components

| Component | Role | Anchors |
|-----------|------|---------|
| **mycobrain_service_standalone** | Serial-first host service; heartbeats to MAS; telemetry to ingest | `services/mycobrain/mycobrain_service_standalone.py` |
| **device_registry_api** | MAS device registry; heartbeat, list, command, CREP entities | `core/routers/device_registry_api.py` |
| **gateway_router** | Jetson gateway; LoRa/BLE/WiFi ingress; heartbeat + telemetry upstream | `edge/gateway_router.py` |
| **ondevice_operator** | Jetson MDP arbiter; approval-gated mutations (firmware/config) | `edge/ondevice_operator.py` |
| **mycobrain_bridge** | MYCA OS ↔ devices; status, telemetry summary | `myca/os/mycobrain_bridge.py` |
| **website /api/mycobrain** | Aggregates local + MAS; CREP device layer source | `WEBSITE/app/api/mycobrain/route.ts` |
| **CREP dashboard** | MycoBrain layer; device-widget-mapper; `/api/mycobrain` | `CREPDashboardClient.tsx` |

---

## CREP Integration

- CREP fetches devices from `/api/mycobrain` (website), which merges:
  - Local MycoBrain service `/devices` when running
  - MAS `/api/devices` when local service is down
- Devices appear in CREP as MycoBrain layer with `UnifiedEntity` type `device`
- New endpoint: `GET /api/devices/crep` returns devices as CREP UnifiedEntity batch for unified entity aggregation

---

## Telemetry Persistence

- Telemetry flows to `TELEMETRY_INGEST_URL` (configured per deployment)
- Supabase ingest per `MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md`
- MINDEX `/api/fci/telemetry` when `MINDEX_API_URL` is set on gateway
- Mycorrhizae publish when `MYCORRHIZAE_API_URL` is set

---

## Commands and Governance

- Device commands: `POST /api/devices/{device_id}/command`
- High-risk mutations (firmware, config): gated in `ondevice_operator` via MutationProposal approval
- MAS forwards commands to device MycoBrain service or Mycorrhizae for gateway-forwarded devices
- Guardian/AVANI gate for device commands: opt-in via `DEVICE_GUARDIAN_GATE_ENABLED`; firmware/config commands require approval when enabled

---

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAS_REGISTRY_URL` | `http://192.168.0.188:8001` | Heartbeat target |
| `TELEMETRY_INGEST_URL` | — | Telemetry ingest API |
| `DEVICE_TTL_SECONDS` | 120 | Device expiry (seconds) |
| `GATEWAY_ID` | `gateway-jetson4` | Gateway identifier |
| `MAS_API_URL` | `http://192.168.0.188:8001` | MAS base (gateway, MYCA) |

---

## Verification

```bash
# MAS device registry
curl -s http://192.168.0.188:8001/api/devices | jq .

# CREP entities (devices as UnifiedEntity)
curl -s http://192.168.0.188:8001/api/devices/crep | jq .

# Website MycoBrain aggregate (local + MAS)
curl -s http://localhost:3010/api/mycobrain | jq .
```

---

## Related Docs

- `INTEGRATION_CONTRACTS_CANONICAL_MAR10_2026.md` — Edge telemetry contract
- `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md` — MDP command families
- `MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md` — Telemetry persistence
- `CSUITE_OPERATOR_CONTRACT_MAR08_2026.md` — Operator/org-state alignment
