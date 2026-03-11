# MDP Internal Rail and Gateway Upstream Protocol Contracts

**Date:** March 7, 2026  
**Status:** Active  
**Related:** `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md`, `GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md`, `MDP_V1_SPECIFICATION_FEB23_2026.md`, `MMP_V1_SPECIFICATION_FEB23_2026.md`

---

## Overview

This doc specifies the **MDP internal rail contracts** (Side A ↔ Jetson16GB ↔ Side B) and the **gateway upstream publish contracts** (4GB Jetson gateway → MAS, Mycorrhizae, MINDEX, website) for the two-Jetson MycoBrain field architecture.

---

## 1. MDP Internal Rail Contracts

The internal device rail uses **MDP v1** exclusively. All frames are COBS-framed with CRC-16.

### 1.1 Legs and Endpoints

| Leg | Source | Dest | Transport | Endpoints (src, dst) |
|-----|--------|------|-----------|----------------------|
| Side A → Jetson16 | Side A | Jetson16 | UART/Serial | SIDE_A (0xA1) → GATEWAY (0xC0) |
| Jetson16 → Side A | Jetson16 | Side A | UART/Serial | GATEWAY (0xC0) → SIDE_A (0xA1) |
| Jetson16 → Side B | Jetson16 | Side B | UART/Serial | GATEWAY (0xC0) → SIDE_B (0xB1) |
| Side B → Jetson16 | Side B | Jetson16 | UART/Serial | SIDE_B (0xB1) → GATEWAY (0xC0) |

**Reference:** `Mycorrhizae/mycorrhizae-protocol/docs/MDP_V1_SPECIFICATION_FEB23_2026.md`

### 1.2 Message Types (MDP)

| Type | Value | Use |
|------|-------|-----|
| TELEMETRY | 0x01 | Sensor data, streaming samples |
| COMMAND | 0x02 | Commands to Side A or Side B |
| ACK | 0x03 | Acknowledgment (when ACK_REQUESTED) |
| EVENT | 0x05 | Device events (estop, fault, link up/down) |
| HELLO | 0x06 | Handshake, identity, capability exchange |

### 1.3 Side A Command Families (Jetson16 → Side A)

Deterministic commands the Jetson cortex may send to Side A. Payload is JSON in MDP frame.

| Command | Payload shape | Side A response |
|---------|---------------|-----------------|
| `read_sensors` | `{"cmd":"read_sensors","params":{"sensors":["bme1","bme2"]}}` | TELEMETRY with sensor readings |
| `enable_peripheral` | `{"cmd":"enable_peripheral","params":{"id":"bme688_1","en":true}}` | ACK |
| `disable_peripheral` | `{"cmd":"disable_peripheral","params":{"id":"bme688_1"}}` | ACK |
| `output_control` | `{"cmd":"output_control","params":{"id":"led1","value":1}}` | ACK |
| `estop` | `{"cmd":"estop","params":{}}` | ACK + EVENT |
| `health` | `{"cmd":"health","params":{}}` | EVENT with health status |
| `stream_sensors` | `{"cmd":"stream_sensors","params":{"rate_hz":1,"sensors":["bme1"]}}` | TELEMETRY stream |

### 1.4 Side B Command Families (Jetson16 → Side B)

Transport directives only. Side B does not interpret application logic.

| Command | Payload shape | Side B response |
|---------|---------------|-----------------|
| `lora_send` | `{"cmd":"lora_send","params":{"payload":"...","qos":1}}` | ACK, EVENT on link state |
| `ble_advertise` | `{"cmd":"ble_advertise","params":{"en":true,"interval_ms":100}}` | ACK |
| `wifi_connect` | `{"cmd":"wifi_connect","params":{"ssid":"...","pass":"..."}}` | ACK, EVENT on connect |
| `sim_send` | `{"cmd":"sim_send","params":{"dest":"...","payload":"..."}}` | ACK |
| `transport_status` | `{"cmd":"transport_status","params":{}}` | EVENT with link/queue state |

### 1.5 Side A → Jetson16 (Upstream)

Side A sends:

- **TELEMETRY**: Sensor readings (`{"ai1":1.2,"temp":22.5,...}`)
- **EVENT**: Estop, fault, peripheral ready
- **HELLO**: Identity, capability manifest, firmware version

### 1.6 Side B → Jetson16 (Upstream)

Side B sends:

- **EVENT**: Link state (LoRa/WiFi/BLE/SIM up/down), queue depth, retry counts
- **TELEMETRY**: Only if Side B has its own diagnostics (e.g. RSSI)
- **ACK**: For COMMANDs with ACK_REQUESTED

### 1.7 Sequence and ACK Rules

- `seq` increments per sender; `ack` echoes received `seq` when acknowledging
- Use `ACK_REQUESTED` flag for commands that require confirmation
- Jetson16 arbitrates: only one COMMAND in flight per leg unless pipelining is explicitly specified

---

## 2. Gateway Upstream Publish Contracts

The 4GB Jetson gateway terminates device traffic from many Side Bs (LoRa, BLE, WiFi, SIM) and publishes upstream. It does **not** replace canonical device identity.

### 2.1 MAS Device Registry

**Endpoint:** `POST http://{MAS_HOST}:8001/api/devices/heartbeat`

**Gateway self-registration** (gateway reports itself):

```json
{
  "device_id": "gateway-{gateway_id}",
  "device_name": "Jetson4 Gateway",
  "device_role": "gateway",
  "host": "{gateway_reachable_ip}",
  "port": 8003,
  "firmware_version": "1.0",
  "board_type": "jetson4",
  "sensors": [],
  "capabilities": ["lora", "ble", "wifi", "sim", "store_and_forward"],
  "connection_type": "lan",
  "ingestion_source": "gateway",
  "extra": {
    "gateway_id": "...",
    "lilygo_node_id": "...",
    "transport_cluster_id": "..."
  }
}
```

**Device relay** (gateway forwards device heartbeats; `device_id` must remain canonical Side A identity):

```json
{
  "device_id": "{canonical_device_id_from_side_a}",
  "device_name": "Mushroom 1",
  "device_role": "mushroom1",
  "host": "{gateway_ip}",
  "port": 8003,
  "ingestion_source": "gateway",
  "extra": {
    "via_gateway_id": "...",
    "transport": "lora"
  }
}
```

**Reference:** `mycosoft_mas/core/routers/device_registry_api.py`, `DeviceHeartbeat` schema

### 2.2 Mycorrhizae Channels / Envelopes

**Protocol:** MMP v1 (evolved from MDP; 32-byte header, SHA256-truncated integrity)

**Usage:** Gateway publishes device telemetry as MMP envelopes with:
- `device_type`: MYCOBRAIN (0x01) for device telemetry; GATEWAY (0x04) for gateway-origin messages
- `device_id`: Canonical device ID from Side A (never gateway ID for device telemetry)
- `payload_type`: TELEMETRY, EVENT, etc.
- Payload: Same JSON shape as MDP telemetry

**Endpoint:** Mycorrhizae API `http://{MYCORRHIZAE_HOST}:8002` (channels/stream) — see Mycorrhizae docs for exact routes.

**Reference:** `MMP_V1_SPECIFICATION_FEB23_2026.md`, `mycorrhizae-protocol/api/`

### 2.3 MINDEX Telemetry / FCI

**Purpose:** Persistent telemetry, FCI (Fungal Computer Interface) observations, analytics.

**Contract:** Gateway forwards device telemetry to MINDEX API or via OEI event bus. Payload shape must match existing telemetry schema:

```json
{
  "deviceId": "{canonical_device_id}",
  "deviceType": "mycobrain",
  "readings": [...],
  "temperature": 22.5,
  "humidity": 65,
  ...
}
```

**Reference:** `MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md`, OEI event bus

### 2.4 Website Ingest API

**Endpoint:** `POST http://{WEBSITE_HOST}:3000/api/devices/ingest` (prod) or `:3010` (dev)

**Payload:** Same as MycoBrain service → ingest today:

```json
{
  "deviceId": "{canonical_device_id}",
  "deviceType": "mycobrain",
  "readings": [{"sensor":"bme1","temperature":22.5,...}],
  "temperature": 22.5,
  "humidity": 65
}
```

**Use case:** Fallback when MAS/MINDEX/Mycorrhizae are unavailable; store-and-forward from gateway buffer.

**Reference:** `MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md`, `WEBSITE/website/app/api/devices/ingest/route.ts`

### 2.5 Identity Rules (Invariants)

- **Canonical `device_id`** always belongs to the MycoBrain / Side A identity
- Gateway has its own `gateway_id`; it may use `device_id: "gateway-{id}"` for self-registration
- When relaying device data, the `device_id` in MAS heartbeat, Mycorrhizae, MINDEX, and ingest must be the **original device identity**, never the gateway
- `extra.via_gateway_id` or similar may record routing for diagnostics

---

## 3. Contract Summary Table

| System | Endpoint / Channel | Auth | Payload key | Identity |
|--------|--------------------|------|-------------|----------|
| MAS | POST /api/devices/heartbeat | (none) | DeviceHeartbeat | device_id = canonical or gateway-{id} |
| Mycorrhizae | MMP envelopes | (per Mycorrhizae) | device_id, payload | device_id = canonical |
| MINDEX | FCI / telemetry API | (per MINDEX) | deviceId | deviceId = canonical |
| Website | POST /api/devices/ingest | optional Bearer | deviceId | deviceId = canonical |

---

## 4. Related Docs

- `MDP_V1_SPECIFICATION_FEB23_2026.md` — MDP frame format, COBS, CRC-16
- `MMP_V1_SPECIFICATION_FEB23_2026.md` — MMP header, integrity, device types
- `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md` — Jetson16 role, arbitration
- `GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md` — Gateway architecture
- `MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md` — End-to-end telemetry flow
