# MycoBrain + Jetson Hardware Plan

**Created:** March 9, 2026
**Status:** Active
**Author:** MYCA Coding Agent

## Overview

Two MycoBrain + Jetson configurations sharing the same firmware and protocol stack:

| Config | Jetson | TOPS | Cost | Power | Use Case |
|--------|--------|------|------|-------|----------|
| **Mushroom 1** | AGX Orin 32GB on reComputer Mini J501 | 200 | ~$1,200 | 15-60W | Lab robot, gateway, manipulator, full perception |
| **Hyphae 1** | Orin Nano 8GB | 40 | ~$275 | 7-15W | Portable field node, battery-viable, lightweight edge AI |

Both share: Side A firmware (sensors), Side B firmware (comms), MDP transport, MMP envelopes, MAS heartbeat, capability-driven website widgets.

---

## Hardware BOM

### Mushroom 1 — Full Robotics Node

| Component | Purpose | Est. Cost |
|-----------|---------|-----------|
| reComputer Mini J501 carrier | Jetson carrier: 10GbE, CAN, RS-485, I2S, GMSL2, 19-48V | $360-400 |
| Jetson AGX Orin 32GB module | 200 TOPS edge AI: NLM, local LLM, Pinocchio IK, camera | $700-800 |
| ESP32-S3 (Side A) | Sensor MCU: BME688, analog, MOSFET, NeoPixel, buzzer, I2C | $8 |
| ESP32-S3 (Side B) | Comms MCU: LoRa, Wi-Fi, BLE, MQTT, store-forward | $8 |
| BME688 | Environmental: temp, humidity, pressure, VOC/gas | $12 |
| SX1262 LoRa module | 868/915 MHz, 15km range | $15 |
| SIM7600X LTE module | Cellular fallback (UART to Side B or USB to Jetson) | $35-50 |
| USB-C cable | Side A ↔ Jetson serial (USB CDC) | $5 |
| GMSL2 camera(s) | Vision (up to 4 simultaneous via J501 expansion) | $50-150 ea |
| SO-ARM101 (optional) | 6 DOF robotic arm, UART, LeRobot/Pinocchio | $200-400 |
| Power supply | 19-48V for J501 | $20-40 |
| Enclosure + wiring | Integration | $30-50 |

**Total: ~$1,200-1,800** depending on camera/arm options.

### Hyphae 1 — Portable Field Node

| Component | Purpose | Est. Cost |
|-----------|---------|-----------|
| Jetson Orin Nano 8GB | 40 TOPS edge AI: NLM embeddings, lightweight inference | $200-275 |
| ESP32-S3 (Side A) | Same firmware as Mushroom 1 | $8 |
| ESP32-S3 (Side B) | Same firmware as Mushroom 1 | $8 |
| BME688 | Environmental sensor | $12 |
| SX1262 LoRa module | Long-range radio | $15 |
| USB-C cable | Side A ↔ Jetson serial | $5 |
| USB camera (optional) | Single USB cam (no GMSL) | $20-40 |
| Battery + solar (optional) | 5V/3A USB-C power bank or solar | $30-60 |

**Total: ~$275-425** depending on options.

---

## Protocol Stack

```
Layer 3: Mycorrhizae   — MQTT topics, Redis pub/sub, cross-device exchange
Layer 2: MMP           — Normalized semantic envelope (device_id, kind, capability_id, measurement_class)
Layer 1: MDP           — COBS framing, CRC16, ACK/retry, typed frames
Layer 0: Physical      — UART, USB-CDC, LoRa radio, Wi-Fi, BLE, LTE
```

### MMP Envelope Schema

```json
{
  "schema": "org.mycosoft.mmp/1",
  "kind": "capability|sample_raw|sample_norm|event|pattern|health|command|command_result",
  "device_id": "MYCOBRAIN-ABC123",
  "producer": "side_a|jetson|side_b|gateway|mas",
  "ts": "2026-03-09T00:00:00Z",
  "capability_id": "bme688_0",
  "measurement_class": "env.air",
  "fields": {},
  "features": {},
  "provenance": {}
}
```

---

## Data Flow

```
Side A (ESP32-S3) — sensors, I2C discovery, local safety, MDP/NDJSON
  │
  ├──[USB-CDC]──→ Jetson (if present)
  │                 NaturePacket assembly, NLM embeddings, camera/depth/arm
  │                 Wraps in MMP envelopes
  │                 Heartbeats to MAS with jetson_present=true
  │                 └──→ Side B (or direct MQTT from Jetson)
  │
  └──[UART]───→ Side B (if Jetson absent — direct bypass)
                  LoRa / Wi-Fi / BLE / LTE
                  MQTT publish MMP envelopes
                  Store-and-forward when offline
                  MAS heartbeat every 30s
                  └──→ MAS (188:8001) /api/devices/heartbeat
                        ├──→ Device Registry + Orchestrator health
                        ├──→ MINDEX (189) for historical storage
                        ├──→ Website Device Manager (capability widgets)
                        └──→ MYCA (query + command)
```

---

## Role Split

| Role | Owner | Responsibilities |
|------|-------|-----------------|
| **Side A** | ESP32-S3 | Sensors, I2C, analog, MOSFET, NeoPixel, buzzer, local safety bounds, capability manifest |
| **Jetson** | AGX Orin / Orin Nano | NLM, NaturePacket, camera, depth, local LLM, IK, MMP bridging |
| **Side B** | ESP32-S3 | LoRa, Wi-Fi, BLE, LTE, MQTT, store-forward, MAS heartbeat |

### Actuation Safety

- Side A enforces local bounds: max voltage, max duration, max rate
- Jetson/MYCA send allow-listed intents only
- Allowed intents: `set_sampling_rate`, `signal_emit`, `pixel_pattern`, `servo_target`, `sensor_rescan`, `stimulus_pulse`, `set_mosfet`, `buzzer_tone`, `buzzer_pattern`, `led_rgb`, `led_off`, `calibrate`, `reset`
- Arm control: Jetson owns IK planning, Side A holds power-enable and emergency stop

---

## Capability-Driven Widgets

Website Device Manager resolves widgets by `measurement_class`:

| measurement_class | Widget | Description |
|-------------------|--------|-------------|
| env.air | environmental_sensor | Temp, humidity, pressure, IAQ gauges |
| bio.electric | bioelectric_timeseries | FCI/analog voltage charts |
| motion.lidar | lidar | Distance + signal strength |
| vision.rgb | camera_feed | Live camera stream |
| actuator.mosfet | switch_panel | On/off toggles |
| actuator.led | color_picker | RGB color control |
| compute.nlm | nlm_dashboard | Embedding + anomaly scores |
| unknown | generic_timeseries | Raw JSON + metadata fallback |

Any I2C sensor plugged into Side A gets auto-discovered, mapped to a measurement_class via the capability manifest, and rendered with the appropriate widget. Unknown sensors get the generic fallback.

---

## Files Modified/Created

| File | Change |
|------|--------|
| `mycosoft_mas/protocols/mmp.py` | **NEW** — MMP envelope, converters, actuation safety |
| `mycosoft_mas/protocols/__init__.py` | Export MMP alongside MDP |
| `mycosoft_mas/core/routers/device_registry_api.py` | `/heartbeat` alias, `peripherals` field, `PeripheralInfo` model |
| `services/mycobrain/jetson_bridge.py` | **NEW** — Jetson-embedded bridge service |
| `services/mycobrain/protocol.py` | `measurement_class` in WIDGET_MAP, `MEASUREMENT_CLASS_WIDGETS`, `resolve_widget_by_measurement_class()` |
| `mycosoft_mas/devices/hyphae1.py` | **NEW** — Hyphae 1 device class |
| `mycosoft_mas/core/routers/fci_api.py` | `bridge_fci_pattern_to_mas()` background task |
| `firmware/MycoBrain_SideA/MycoBrain_SideA.ino` | v2.0.0: capability_manifest, bus_rescan, safety bounds, stimulus_pulse |
| `firmware/MycoBrain_SideB/MycoBrain_SideB.ino` | v2.0.0: Wi-Fi, MQTT publish, LoRa relay, store-forward, LTE stub |

---

## Verification Plan

Test in order: serial → Jetson → backhaul → gateway → LTE

1. `pio device monitor -b 115200` — Side A emits capability_manifest on boot
2. `curl http://localhost:8003/health` — MycoBrain service running
3. Start `jetson_bridge.py` — verify NaturePacket + NLM embedding
4. `curl http://192.168.0.188:8001/api/devices` — device registered with peripherals
5. Website Device Manager — capability-driven widgets render
6. FCI pattern → appears under same device_id in MAS and MINDEX
7. Two MycoBrain units → LoRa relay through gateway
8. SIM7600X → MQTT publish over cellular
9. Meshtastic bridge (optional, gateway-side adapter)
