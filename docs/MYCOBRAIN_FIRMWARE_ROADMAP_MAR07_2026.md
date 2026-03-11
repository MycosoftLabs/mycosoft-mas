# MycoBrain Side A and Side B Firmware Roadmap

**Date:** March 7, 2026  
**Status:** Active  
**Related:** `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`, `MYCOBRAIN_FIRMWARE_BASELINE_REBASELINE_MAR07_2026.md`, `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md`, Jetson-Backed MycoBrain Field Architecture Plan

---

## Overview

This roadmap plans the Side A and Side B firmware refactors required for the two-Jetson MycoBrain field architecture. Side A becomes a deterministic MDP command executor; Side B becomes a transport-only executor with LoRa/BLE/WiFi/SIM primitives.

---

## Current State

### Side A (MycoBrain_SideA.ino)

| Capability | Status | Notes |
|------------|--------|-------|
| BME688 (2x) | ✅ | I2C 0x76, 0x77 |
| I2C scan | ✅ | `scan`, `i2c_scan` |
| Analog inputs (AI1–AI4) | ✅ | |
| MOSFET outputs (3x) | ✅ | `set_mosfet` |
| NeoPixel (GPIO15) | ✅ | Basic control |
| Buzzer | ✅ | `buzzer`, `buzz` |
| Telemetry (NDJSON) | ✅ | `sendTelemetry()` |
| JSON commands | ✅ | `cmd` key parsing |
| Machine mode | ✅ | Website compatibility |
| **MDP framing** | ❌ | Plain Serial line JSON only |
| **HELLO/capability manifest** | ❌ | No structured identity |
| **MDP seq/ack** | ❌ | No sequence or ACK protocol |
| **estop** | ❌ | Not implemented |
| **stream_sensors** | ❌ | Interval-based only, no rate_hz |
| **enable/disable_peripheral** | ❌ | No dynamic peripheral enable |

### Side B (MycoBrain_SideB.ino)

| Capability | Status | Notes |
|------------|--------|-------|
| UART relay to Side A | ✅ | Serial1 RX/TX |
| PC ↔ Side A passthrough | ✅ | Line-based JSON forward |
| Side A heartbeat | ✅ | 5s timeout |
| **MDP framing** | ❌ | Plain line JSON |
| **LoRa** | ❌ | Not implemented |
| **BLE** | ❌ | Not implemented |
| **WiFi** | ❌ | Not implemented |
| **SIM/modem** | ❌ | Not implemented |
| **Transport directives** | ❌ | No `lora_send`, `ble_advertise`, etc. |
| **Jetson16 as peer** | ❌ | Assumes PC on Serial; needs UART to Jetson |

---

## Side A Refactor Plan

### Phase 3a: MDP Layer (Prerequisite)

1. **Add MDP framing**
   - Include `mdp_types.h` (from mycobrain/firmware/common or port)
   - Implement COBS encode/decode
   - Implement CRC-16 (CCITT-FALSE)
   - Serial becomes MDP frame stream; Jetson16 speaks MDP on UART

2. **Add seq/ack handling**
   - Per-leg sequence (`seq`) and echo (`ack`)
   - ACK_REQUESTED for commands requiring confirmation
   - ACK frame on success; NACK on parse/execution failure

3. **Add HELLO and capability manifest**
   - On boot or HELLO request: send HELLO frame with:
     - `device_id` (MAC or configured ID)
     - `firmware_version`, `role`: "side_a"
     - `capabilities`: `["bme688", "i2c", "analog", "mosfet", "neopixel", "buzzer"]`
     - `sensors`: `["bme1", "bme2", "ai1", "ai2", "ai3", "ai4"]`

### Phase 3b: Command Family Alignment

Map existing commands to MDP contract (see `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`):

| MDP Command | Current | Action |
|-------------|---------|--------|
| `read_sensors` | `read_sensor`, `scan` | Unify into `read_sensors` with `params.sensors` array |
| `enable_peripheral` | — | Add; gate BME688/I2C peripheral init |
| `disable_peripheral` | — | Add |
| `output_control` | `set_mosfet`, LED, buzzer | Map to generic `output_control` with `id` |
| `estop` | — | Add; safe all outputs, stop streaming |
| `health` | `status` | Alias or extend to MDP EVENT |
| `stream_sensors` | Interval-based telemetry | Add configurable `rate_hz`, selective sensors |

### Phase 3c: Determinism and Safety

1. **Command arbitration**
   - Side A obeys one commander (Jetson16 via UART)
   - Reject or queue conflicting commands
   - Estop overrides everything

2. **Event emission**
   - Emit MDP EVENT for: estop, fault, peripheral ready, health change
   - Structured payload per `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`

---

## Side B Refactor Plan

### Phase 4a: MDP Layer and Jetson16 as Peer

1. **Replace PC Serial with Jetson16 UART**
   - Current: Serial (PC), UART_TO_SIDEA (Side A)
   - Target: UART_JETSON (Jetson16), UART_TO_SIDEA (Side A)
   - Side B receives MDP frames from Jetson16; forwards to Side A or executes transport directives

2. **MDP framing**
   - Same COBS/CRC-16 as Side A
   - Endpoints: SIDE_B (0xB1), GATEWAY (0xC0)

3. **Dual UART topology**
   - UART1: Jetson16 ↔ Side B (MDP)
   - UART2: Side B ↔ Side A (MDP relay or pass-through initially)

### Phase 4b: Transport Directive Handlers

Implement only the **directive** interface; no application logic:

| Directive | Hardware | Implementation |
|-----------|----------|----------------|
| `lora_send` | LilyGO SX1262 or similar | Enqueue payload; send via LoRa; ACK on TX done |
| `ble_advertise` | ESP32 BLE | Start/stop BLE advertising |
| `wifi_connect` | ESP32 WiFi | Connect to SSID; EVENT on connect/fail |
| `sim_send` | Modem (e.g., SIM7080) | Enqueue; send via modem; ACK |
| `transport_status` | — | Return EVENT with link state, queue depth |

### Phase 4c: Link-State Reporting

- Side B emits EVENT for: LoRa link up/down, BLE/WiFi/SIM state, queue depth, retry counts
- Jetson16 uses this for routing and backpressure

### Phase 4d: No Application Logic

- Side B does **not** parse sensor data, run logic, or make decisions
- It only: relay MDP frames to/from Side A, execute transport directives, report link state

---

## Implementation Order

| Phase | Firmware | Deliverable | Dependencies |
|-------|----------|-------------|--------------|
| 3a | Side A | MDP framing, seq/ack, HELLO | mdp_types.h, COBS, CRC-16 |
| 3b | Side A | MDP command family alignment | 3a |
| 3c | Side A | Estop, events, determinism | 3b |
| 4a | Side B | MDP + Jetson16 UART topology | mdp_types.h, COBS, CRC-16 |
| 4b | Side B | Transport directives (LoRa first) | 4a, LoRa hardware |
| 4c | Side B | Link-state EVENTs | 4b |
| 4d | Side B | Remove any app logic | 4a–4c |

---

## Shared Components

### mdp_types.h and MDP Library

- **Source:** `mycobrain/firmware/common/mdp_types.h` (or equivalent in MAS/firmware)
- **Needed:** COBS encode/decode, CRC-16, frame build/parse
- **Action:** Ensure Side A and Side B both use the same MDP library; add to PlatformIO lib_deps if needed

### JSON Payload Convention

- All MDP payloads remain JSON (per MDP v1 spec)
- Command shape: `{"cmd":"...", "params":{...}}`
- Response: TELEMETRY, ACK, or EVENT with consistent keys

---

## Risk and Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking DeviceManager/DualMode | Keep DeviceManager as operational baseline; Side A refactor is additive branch |
| Side B hardware (LoRa, modem) not ready | Implement UART+MDP first; add transport directives incrementally as hardware arrives |
| Jetson16 not yet deployed | Side A can still speak MDP to PC/serial for dev; Side B can relay PC↔Side A during dev |

---

## Verification

1. **Side A**: Jetson16 (or PC with MDP client) sends `read_sensors`; receives TELEMETRY. Send `estop`; all outputs safe.
2. **Side B**: Jetson16 sends `lora_send`; Side B ACKs and emits EVENT on TX. No application parsing of payload.
3. **Identity**: HELLO from Side A contains canonical device_id; gateway never substitutes it.

---

## Related Docs

- `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md` — Command families, gateway contracts
- `MDP_V1_SPECIFICATION_FEB23_2026.md` — Frame format, COBS, CRC-16
- `MYCOBRAIN_FIRMWARE_BASELINE_REBASELINE_MAR07_2026.md` — Baseline landscape
- `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md` — Jetson16 role
- `GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md` — Gateway hardware context
