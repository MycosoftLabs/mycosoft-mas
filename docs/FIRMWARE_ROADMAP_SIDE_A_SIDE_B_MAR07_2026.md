# Firmware Roadmap: Side A and Side B Refactors

**Date:** March 7, 2026  
**Status:** Active  
**Related Plan:** Jetson-Backed MycoBrain Field Architecture  
**Related Docs:** `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`, `MYCOBRAIN_FIRMWARE_BASELINE_REBASELINE_MAR07_2026.md`, `SIDE_B_TRANSPORT_AND_BACKHAUL_MAR07_2026.md`

---

## Overview

This document plans the firmware refactors for **Side A** (sensing/control) and **Side B** (transport) under the two-Jetson MycoBrain field architecture. The target is deterministic control and transport execution: Side A responds only to MDP-defined commands; Side B executes transport directives only, with no application logic.

---

## Current State

### Side A (`MycoBrain_SideA`)

| Aspect | Current | Target |
|--------|---------|--------|
| Protocol | JSON/NDJSON over serial | MDP v1 frames (COBS + CRC-16) |
| Commands | `{"cmd":"..."}` ad-hoc | Deterministic MDP command families |
| Sensing | BME688, I2C scan, AI1–AI4 | Same + explicit `read_sensors` / `stream_sensors` |
| Outputs | MOSFET, NeoPixel, Buzzer | Same + explicit `output_control` |
| Identity | MAC in telemetry | HELLO with identity + capability manifest |
| Health | status command | `health` MDP command + EVENT |

### Side B (`MycoBrain_SideB`)

| Aspect | Current | Target |
|--------|---------|--------|
| Protocol | Raw JSON passthrough | MDP v1 frames (COBS + CRC-16) |
| Role | UART relay (PC ↔ Side A) | Transport executor only |
| Transport | UART only | UART + LoRa + BLE + WiFi + SIM directives |
| Logic | Command routing, status | No application logic; execute `lora_send`, `ble_advertise`, etc. |

---

## Phase 3: Side A Firmware Refactor

### 3.1 MDP Frame Layer

**Goal:** Replace JSON-over-serial with MDP v1 framing.

| Task | Description | Deps |
|------|-------------|------|
| MDP lib | Add MDP encode/decode (COBS, CRC-16, header) to Side A | MDP spec |
| Frame rx | Parse incoming MDP frames from UART; validate CRC; dispatch by msg_type | MDP lib |
| Frame tx | Emit TELEMETRY, EVENT, HELLO, ACK as MDP frames | MDP lib |
| Backward mode | Optional: legacy JSON mode for DeviceManager compatibility during transition | — |

**Reference:** `MDP_V1_SPECIFICATION_FEB23_2026.md`, `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md` §1.3

### 3.2 Deterministic Command Families

**Goal:** Implement Side A command families from protocol contracts.

| Command | Payload | Implementation |
|---------|---------|----------------|
| `read_sensors` | `{"cmd":"read_sensors","params":{"sensors":["bme1","bme2"]}}` | Call BME688 read; return TELEMETRY |
| `enable_peripheral` | `{"cmd":"enable_peripheral","params":{"id":"bme688_1","en":true}}` | Enable/disable BME688, MOSFET, etc. |
| `disable_peripheral` | `{"cmd":"disable_peripheral","params":{"id":"bme688_1"}}` | Disable peripheral |
| `output_control` | `{"cmd":"output_control","params":{"id":"led1","value":1}}` | Map to MOSFET/NeoPixel/Buzzer |
| `estop` | `{"cmd":"estop","params":{}}` | Disable outputs; emit EVENT |
| `health` | `{"cmd":"health","params":{}}` | Return EVENT with uptime, peripherals, faults |
| `stream_sensors` | `{"cmd":"stream_sensors","params":{"rate_hz":1,"sensors":["bme1"]}}` | Configurable telemetry stream |

**Migration:** Map existing `status`, `scan`, `led`, `buzzer`, `power` to these families where applicable; deprecate ad-hoc commands.

### 3.3 BME688 and Peripheral Support

**Goal:** Complete and stabilize sensor/peripheral support.

| Task | Description |
|------|-------------|
| BME688 dual | Support both 0x76 and 0x77; `read_sensors` with `sensors:["bme1","bme2"]` |
| Analog inputs | AI1–AI4 in `read_sensors` and TELEMETRY |
| I2C scan | Expose via `health` or dedicated capability; `enable_peripheral` for discovered devices |
| Output mapping | Define stable `id` for MOSFET_1/2/3, led1, buzzer in `output_control` |
| Calibration | Optional: store calibration offsets in NVS for BME688 |

### 3.4 Output/Sensor/Motion Command Families

**Goal:** Explicit, extensible command surface.

| Family | Commands | Notes |
|--------|----------|-------|
| Sensors | `read_sensors`, `stream_sensors` | BME688, AI, future sensors |
| Outputs | `output_control`, `enable_peripheral`, `disable_peripheral` | MOSFET, LED, Buzzer |
| Safety | `estop`, `health` | No application logic; deterministic response |
| Motion | (future) `motor_set`, `servo_set` | Placeholder for locomotion/motion surfaces |

### 3.5 HELLO and Identity

**Goal:** Side A owns canonical device identity.

| Task | Description |
|------|-------------|
| HELLO on boot | Send HELLO with MAC, firmware version, capability manifest |
| Capability manifest | List sensors, outputs, transport endpoints (e.g. UART to Side B) |
| Identity source | MAC + role (mushroom1, etc.) as canonical `device_id`; Jetson16 must not replace |

---

## Phase 4: Side B Firmware Refactor

### 4.1 MDP Frame Layer

**Goal:** Same as Side A — MDP v1 framing for all communication.

| Task | Description |
|------|-------------|
| MDP lib | Shared or duplicated MDP encode/decode |
| Frame rx | Parse MDP COMMAND from Jetson16 (or PC during dev); validate CRC |
| Frame tx | Emit ACK, EVENT as MDP frames; forward TELEMETRY from Side A in MDP if needed |
| UART to Side A | Today: raw JSON. Future: MDP frames (Side A speaks MDP) |
| UART to Jetson16 | MDP frames only |

### 4.2 Transport Executor Role

**Goal:** Side B executes transport directives only. No sensing, no application logic.

| Command | Payload | Implementation |
|---------|---------|----------------|
| `lora_send` | `{"cmd":"lora_send","params":{"payload":"...","qos":1}}` | Enqueue LoRa TX; ACK when queued; EVENT on link state |
| `ble_advertise` | `{"cmd":"ble_advertise","params":{"en":true,"interval_ms":100}}` | Start/stop BLE advertising |
| `wifi_connect` | `{"cmd":"wifi_connect","params":{"ssid":"...","pass":"..."}}` | Connect WiFi; EVENT on connect/fail |
| `sim_send` | `{"cmd":"sim_send","params":{"dest":"...","payload":"..."}}` | Cellular modem send (future) |
| `transport_status` | `{"cmd":"transport_status","params":{}}` | Return EVENT with link/queue state |

**No logic beyond:** parse directive → execute transport primitive → ACK/EVENT.

### 4.3 LoRa Integration

**Goal:** Add LoRa (SX1262) as first non-UART transport.

| Task | Description |
|------|-------------|
| Hardware | SX1262 on LilyGO or similar; SPI to Side B ESP32 |
| Driver | Use RadioLib or equivalent; init, TX, RX |
| `lora_send` | Send payload; report link state via EVENT |
| RX path | Receive from gateway/LilyGO; forward to Jetson16 as MDP or raw |
| Queue | Store-and-forward queue when uplink unavailable (configurable depth) |

**Reference:** `SIDE_B_TRANSPORT_AND_BACKHAUL_MAR07_2026.md`, `GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md`

### 4.4 BLE Integration

**Goal:** BLE for local proximity (config, diagnostics).

| Task | Description |
|------|-------------|
| `ble_advertise` | Start/stop BLE advertising with configurable interval |
| GATT | Optional: expose transport_status, device_id for local tools |
| No application logic | BLE is transport only; no sensing interpretation |

### 4.5 WiFi Integration

**Goal:** WiFi for local gateway when LoRa not used.

| Task | Description |
|------|-------------|
| `wifi_connect` | Connect to AP; EVENT on success/failure |
| TCP/UDP | Optional: socket to gateway for relay |
| Fallback | When Ethernet/WiFi available, use instead of LoRa |

### 4.6 SIM/Cellular (Future)

**Goal:** Cellular modem for field deployment.

| Task | Description |
|------|-------------|
| Modem | AT command driver for SIM7080 or similar |
| `sim_send` | Send payload via modem |
| Integration | Same store-and-forward as LoRa |

---

## Dependency Order

```
Phase 3 (Side A):
  MDP lib → Frame rx/tx → Command families → BME688/peripherals → HELLO/identity

Phase 4 (Side B):
  MDP lib → Frame rx/tx → lora_send (first transport) → ble_advertise, wifi_connect → sim_send (later)
```

**Cross-dependency:** Side B refactor can proceed in parallel once MDP lib is defined. Side A and Side B can share MDP encode/decode code (e.g. Arduino library or common C module).

---

## Milestones

| Milestone | Side A | Side B | Date target |
|-----------|--------|--------|-------------|
| M1: MDP framing | MDP rx/tx working | MDP rx/tx working | TBD |
| M2: Deterministic commands | All Side A families implemented | Transport directives (UART relay only) | TBD |
| M3: LoRa | — | `lora_send` + link state | TBD |
| M4: Full transport | — | BLE, WiFi, optional SIM | TBD |
| M5: HELLO/identity | HELLO on boot, capability manifest | — | TBD |

---

## Testing Strategy

| Level | Side A | Side B |
|-------|--------|--------|
| Unit | MDP encode/decode, CRC | MDP encode/decode, transport queue |
| Integration | Jetson16 → Side A MDP commands | Side B → LoRa TX; gateway RX |
| System | Full device: Side A + Jetson16 + Side B + gateway | Same |
| Backward | Legacy JSON mode still works during transition | UART passthrough for non-MDP clients |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| MDP lib bugs | Reuse/port from existing Mycorrhizae or MAS MDP code; unit test CRC and COBS |
| Side B becomes stateful | Enforce: Side B has no application state beyond transport queue and link state |
| Breaking DeviceManager | Keep legacy JSON mode in Side A until all consumers migrated |
| LoRa range/reliability | Gateway store-and-forward; Side B queue with retry |

---

## Related Documents

- [MDP_PROTOCOL_CONTRACTS_MAR07_2026.md](./MDP_PROTOCOL_CONTRACTS_MAR07_2026.md) — Command families, gateway contracts
- [MYCOBRAIN_FIRMWARE_BASELINE_REBASELINE_MAR07_2026.md](./MYCOBRAIN_FIRMWARE_BASELINE_REBASELINE_MAR07_2026.md) — Firmware baseline
- [SIDE_B_TRANSPORT_AND_BACKHAUL_MAR07_2026.md](./SIDE_B_TRANSPORT_AND_BACKHAUL_MAR07_2026.md) — Transport strategy
- [GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md](./GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md) — Gateway architecture
- [MDP_V1_SPECIFICATION_FEB23_2026.md](../Mycorrhizae/mycorrhizae-protocol/docs/MDP_V1_SPECIFICATION_FEB23_2026.md) — MDP frame format
