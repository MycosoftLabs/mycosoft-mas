# Device Network Edge-Cortex and Gateway Awareness

**Date:** March 7, 2026  
**Status:** Active  
**Related:** `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`, `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md`, `GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md`, `MYCOBRAIN_CAPABILITY_MANIFEST_MAR07_2026.md`

---

## Overview

Device Manager, Device Network, NatureOS, and capability models must reflect **edge-cortex** (16GB Jetson on-device) and **gateway** (4GB Jetson + LilyGO) roles without breaking canonical device identity. This document specifies the extensions and invariants.

---

## Identity Invariants (Never Break)

1. **Canonical `device_id`** always belongs to the MycoBrain / Side A identity
2. Gateway has its own identity (`gateway-{id}`) for self-registration
3. When a gateway relays device data, the `device_id` in MAS, Mycorrhizae, MINDEX, and ingest must be the **original device identity**, never the gateway
4. `extra.via_gateway_id` may record routing for diagnostics but does not replace identity

---

## Role and Capability Extensions

### Edge-Cortex (Jetson16 on-device)

Devices with a 16GB Jetson mounted on-board have an optional **edge cortex** capability. This does not change device identity.

| Field | Value | Notes |
|-------|-------|-------|
| `capabilities` | Add `edge_cortex` | Reported by Jetson16 or derived from `board_type` |
| `board_type` | `jetson16` or `esp32s3+jetson16` | When Jetson16 is present |
| `extra.edge_operator_id` | Optional | Operator session identifier |
| `extra.local_model` | Optional | Edge model name |

**Display:** "Edge Cortex" badge or indicator when `edge_cortex` in capabilities. Device still shows as Mushroom 1, SporeBase, etc.

### Gateway (4GB Jetson + LilyGO)

| Field | Value | Notes |
|-------|-------|-------|
| `device_role` | `gateway` | For 4GB Jetson gateway nodes |
| `capabilities` | `lora`, `ble`, `wifi`, `sim`, `store_and_forward` | Per GATEWAY doc |
| `board_type` | `jetson4` | 4GB Jetson |
| `ingestion_source` | `gateway` | |
| `extra.gateway_id` | Gateway unique ID | |
| `extra.transport_cluster_id` | Optional | Site cluster |

**Display:** "Gateway" role; distinct card/section in topology when multiple device types shown.

### Relayed Devices (via Gateway)

When a device reaches MAS via a gateway:

| Field | Value | Notes |
|-------|-------|-------|
| `device_id` | **Canonical device ID** (unchanged) | From Side A |
| `ingestion_source` | `gateway` | |
| `extra.via_gateway_id` | Gateway ID | For diagnostics |
| `extra.transport` | `lora`, `ble`, `wifi`, `sim` | How device reached gateway |

**Display:** Device shows normally (Mushroom 1, etc.) with optional "via Gateway" or transport icon when `via_gateway_id` present.

---

## Capability Manifest Updates

### MAS `capability_manifest.py`

- **gateway**: Add `store_and_forward`, `sim` to capabilities
- **mushroom1** (when Jetson16): Add `edge_cortex` — either as conditional or new role `mushroom1-cortex`

For simplicity, `edge_cortex` is a **capability** that can be added to any role when the device reports it (e.g. in heartbeat `capabilities`). No new role required.

### Website `device-products.ts`

- **CAPABILITY_DISPLAY**: Add `edge_cortex`, `store_and_forward`, `sim`
- **DEVICE_ROLE_DISPLAY**: `gateway` already present

---

## Device Network UI Behavior

### Topology View

1. **Gateway nodes**: Show as distinct "Gateway" nodes when `device_role === "gateway"`
2. **Edge-cortex devices**: Optional badge/icon when `capabilities` includes `edge_cortex`
3. **Relayed devices**: Show transport icon (LoRa, BLE, etc.) when `extra.transport` or `extra.via_gateway_id` present

### Device Cards

- **Gateway**: Use `formatDeviceRole("gateway")` → "Gateway"
- **Capability badges**: Render `edge_cortex`, `store_and_forward`, `sim` from CAPABILITY_DISPLAY

### Filters / Grouping

- Filter by "Gateway" vs "Devices" (optional)
- Group by connection type (serial, lora, wifi, gateway-relay)

---

## NatureOS Integration

NatureOS device views should:

1. Consume `device_role`, `capabilities`, `ingestion_source`, `extra` from MAS network API
2. Display gateway and edge-cortex indicators when present
3. Never substitute gateway ID for device ID in telemetry or control routes

---

## Implementation Checklist

| Item | Location | Status |
|------|----------|--------|
| Gateway capabilities (store_and_forward, sim) | capability_manifest.py | Done |
| edge_cortex capability display | device-products.ts | Done |
| store_and_forward, sim display | device-products.ts | Done |
| Gateway topology section | network/page.tsx | Optional; gateway role already in roleMap |
| Relayed device indicator | network/page.tsx | Optional; use extra.via_gateway_id |

---

## Related Docs

- `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md` — Identity rules, gateway heartbeat shape
- `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md` — Edge cortex role
- `GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md` — Gateway capabilities
- `MYCOBRAIN_CAPABILITY_MANIFEST_MAR07_2026.md` — Manifest contract
- `DEVICE_UI_VERIFICATION_COMPLETE_MAR07_2026.md` — Current UI verification
