# MycoBrain → Jetson → MYCA Server Gateway Build Plan

**Date:** March 7, 2026  
**Status:** Plan (Ready for Build)  
**Scope:** Hardware, firmware, and connection plan for three Jetson tiers: Mushroom 1, Hyphae 1, Gateway

---

## Table of Contents

1. [Overview](#1-overview)
2. [Tier Assignment and Capabilities](#2-tier-assignment-and-capabilities)
3. [Tier 1 — Mushroom 1 (Yahboom Orin NX Super)](#3-tier-1--mushroom-1-yahboom-orin-nx-super)
4. [Tier 2 — Hyphae 1 (Waveshare Jetson Nano/Xavier NX)](#4-tier-2--hyphae-1-waveshare-jetson-nanoxavier-nx)
5. [Tier 3 — Gateway Node (Jetson Nano B01 4GB)](#5-tier-3--gateway-node-jetson-nano-b01-4gb)
6. [Connection Architecture](#6-connection-architecture)
7. [Big Device Power Setup (12V Solar + Battery)](#7-big-device-power-setup-12v-solar--battery)
8. [MycoBrain Firmware Configuration per Tier](#8-mycobrain-firmware-configuration-per-tier)
9. [Software Stack per Jetson](#9-software-stack-per-jetson)
10. [Step-by-Step Build Instructions](#10-step-by-step-build-instructions)
11. [Testing and Verification](#11-testing-and-verification)
12. [BOM Summary](#12-bom-summary)

---

## 1. Overview

This plan connects **MycoBrain** dual-ESP32 hardware to **NVIDIA Jetson** boards at three capability tiers, forming a gateway into the **MYCA server** (MAS at 192.168.0.188:8001, MycoBrain service on port 8003).

| Tier | Device Role | Jetson Board | Compute | Primary Use |
|------|-------------|--------------|---------|-------------|
| 1 | **Mushroom 1** | Yahboom Orin NX Super 157TOPS | 117–157 TOPS | Direct USB → PC → Switch → Server (testing) |
| 2 | **Hyphae 1** | Waveshare Jetson Nano/Xavier NX | ~0.5–21 TOPS | Via Gateway (WiFi + LoRa testing) |
| 3 | **Gateway** | Jetson Nano B01 4GB | ~0.5 TOPS | Gateway node into MYCA server |

**Key flows:**
- **Mushroom 1:** MycoBrain USB-C → PC (USB serial) → Switch (Ethernet) → Server. MycoBrain service on PC or Server ingests serial.
- **Hyphae 1:** MycoBrain → WiFi/LoRa → Gateway (Jetson Nano) → Ethernet/WiFi → MYCA Server.
- **Gateway:** LoRa receiver + USB serial from MycoBrain (optional direct) → forwards to MAS heartbeat/ingestion.

---

## 2. Tier Assignment and Capabilities

### Tier 1 — Mushroom 1 (Best)
- **Jetson:** Yahboom Jetson Orin NX Super (157 TOPS, 8GB/16GB RAM)
- **Role:** Primary lab device, full AI (voice, vision), direct server connection
- **Connection:** MycoBrain USB → PC → Switch → Server (hardwired testing)

### Tier 2 — Hyphae 1 (Second Best)
- **Jetson:** Waveshare Jetson Nano/Xavier NX (16GB eMMC, optional Xavier NX)
- **Role:** Field/mobile device, WiFi + LoRa backhaul
- **Connection:** MycoBrain → Gateway (LoRa/WiFi) → MYCA Server

### Tier 3 — Gateway (Third Best)
- **Jetson:** Jetson Nano B01 4GB (official dev kit)
- **Role:** LoRa/WiFi gateway, aggregates Hyphae 1 and other remote devices
- **Connection:** Gateway → Ethernet/WiFi → MYCA Server (192.168.0.188)

---

## 3. Tier 1 — Mushroom 1 (Yahboom Orin NX Super)

### 3.1 Hardware BOM

| Item | Spec / Part | Qty | Est. $ | Notes |
|------|-------------|-----|--------|-------|
| Jetson Orin NX Super | Yahboom Jetson Orin NX Super 157TOPS, 8GB/16GB RAM, 256GB M.2 SSD, AI Voice Module, IMX219 camera | 1 | ~$400–600 | [Amazon B0FQ5XWXMG](https://www.amazon.com/dp/B0FQ5XWXMG) |
| MycoBrain dual-ESP32 | Side A + Side B, BME688, SX1262 LoRa, NeoPixel, buzzer | 1 | (existing) | See mycobrain firmware |
| USB-C cable | USB 2.0/3.0, data-capable, MycoBrain → PC | 1 | ~$5 | Use Side B USB (UART-2) or Side A USB (UART-0) |
| PC (dev/test) | Windows/Linux with USB serial | 1 | (existing) | Runs MycoBrain service or proxies to server |
| Ethernet | PC → Switch → Server | — | (existing) | 192.168.0.x LAN |

### 3.2 Connection Diagram

```
[MycoBrain Mushroom 1]
       │ USB-C (115200 baud)
       ▼
[PC - COM port / /dev/ttyUSBx]
       │ MycoBrain service (port 8003) OR serial forward
       │ Ethernet
       ▼
[Switch] ──────────────────► [MYCA Server 192.168.0.188:8001]
                                    [MycoBrain Service 8003]
```

### 3.3 Firmware

- **MycoBrain Side A:** `mushroom1` role, BME688, NeoPixel, buzzer
- **MycoBrain Side B:** `mushroom1` role, `ENABLE_WIFI=1`, `ENABLE_LORA=0` (or 1 for dual-path)
- **Baud:** 115200

---

## 4. Tier 2 — Hyphae 1 (Waveshare Jetson Nano/Xavier NX)

### 4.1 Hardware BOM

| Item | Spec / Part | Qty | Est. $ | Notes |
|------|-------------|-----|--------|-------|
| Jetson Nano/Xavier NX Kit | Waveshare Dev Kit, 16GB eMMC, Nano or Xavier NX core | 1 | ~$150–250 | [Amazon B09TXL8NQ5](https://www.amazon.com/dp/B09TXL8NQ5) |
| MycoBrain dual-ESP32 | Side A + Side B, BME688, SX1262, LoRa + WiFi | 1 | (existing) | Hyphae 1 build |
| LoRa SX1262 module | 915 MHz (or regional) | 1 | ~$15 | On MycoBrain or external if gateway |
| Power | 5V 4A micro-USB or barrel (Waveshare) | 1 | ~$15 | Or from Big Device buck |

### 4.2 Connection Diagram

```
[MycoBrain Hyphae 1]  ──LoRa──► [Gateway Jetson Nano]
        │                              │
        └────── WiFi ──────────────────┘
                              │
                              ▼
                    [MYCA Server 192.168.0.188]
```

### 4.3 Firmware

- **MycoBrain Side A:** `hyphae1` role
- **MycoBrain Side B:** `hyphae1` role, `ENABLE_LORA=1`, `ENABLE_WIFI=1`
- LoRa: 915 MHz, SF7–SF12, BW 125 kHz (match gateway)

---

## 5. Tier 3 — Gateway Node (Jetson Nano B01 4GB)

### 5.1 Hardware BOM

| Item | Spec / Part | Qty | Est. $ | Notes |
|------|-------------|-----|--------|-------|
| Jetson Nano B01 | 4GB RAM, official dev kit | 1 | ~$99–150 | [Amazon B0BNQDV3FR](https://www.amazon.com/dp/B0BNQDV3FR) |
| LoRa receiver | SX1262 or RAK3172/Seeed module, USB or GPIO | 1 | ~$25–40 | For LoRa uplink from Hyphae 1 |
| USB-UART adapter | CP2102/CH340, 3.3V, if MycoBrain direct-connect | 1 | ~$5 | Optional: local MycoBrain via USB |
| Ethernet cable | Gateway → Switch → Server | 1 | ~$5 | Or WiFi if no Ethernet |
| Power | 5V 4A barrel | 1 | ~$15 | Or from Big Device buck |

### 5.2 Connection Diagram

```
[LoRa packets from Hyphae 1] ──► [Gateway Jetson Nano]
                                        │
[MycoBrain via USB - optional] ──────────┤
                                        │ Ethernet / WiFi
                                        ▼
                              [MYCA Server 192.168.0.188]
                              - MycoBrain service 8003
                              - MAS heartbeat 8001
```

### 5.3 Software Role

- Run **MycoBrain serial proxy** or **LoRa→HTTP bridge** on Jetson
- Forward MDP telemetry to `http://192.168.0.188:8003/api/telemetry` or equivalent
- Optional: run light MycoBrain-compatible ingestion service on Jetson

---

## 6. Connection Architecture

### 6.1 Setup A: Mushroom 1 Direct (Testing)

```
MycoBrain Mushroom 1 (USB) ──► PC ──► Switch ──► Server
```

- **PC:** Run MycoBrain service (`mycobrain_service_standalone.py`) with `MYCOBRAIN_SERIAL_PORT=COMx` (Windows) or `/dev/ttyUSB0` (Linux)
- **Server:** MAS at 192.168.0.188:8001 receives heartbeats from MycoBrain service
- **Alternative:** Run MycoBrain service on Server; PC runs serial-over-network forward (e.g. `socat`)

### 6.2 Setup B: Hyphae 1 via Gateway (Testing)

```
MycoBrain Hyphae 1 ──LoRa──► Gateway Jetson Nano ──Ethernet──► Server
                  ──WiFi───► (optional direct to server)
```

- **Gateway:** LoRa RX → parse MDP → HTTP POST to Server
- **WiFi:** Hyphae 1 Side B can WiFi to Server if in range (future: WiFi ingestion endpoint)

### 6.3 Setup C: Gateway as MYCA Edge Node

```
[LoRa devices] ──► [Gateway Jetson Nano] ──► [192.168.0.188 MAS]
[USB MycoBrain] ──► (optional)
```

- Gateway runs 24/7, aggregates LoRa, forwards to MAS

---

## 7. Big Device Power Setup (12V Solar + Battery)

For **field/deployable** builds (Hyphae 1, Gateway, or solar-powered Mushroom 1):

### 7.1 BOM

| Item | Spec | Qty | Est. $ | Notes |
|------|------|-----|--------|-------|
| Solar panel | 12V, 10–20W+ | 1 | ~$30–60 | Match load |
| RITAR battery | 12V sealed lead-acid | 1 | (existing) | User-provided |
| Solar charge controller | Renogy Wanderer 10A PWM | 1 | ~$25 | [Renogy Wanderer](https://www.renogy.com) |
| Buck converter | 12V → 3.3V + 5V, multi-output | 1 | ~$4–5 | [DC-DC 12V to 3.3V/5V](https://www.google.com/search?q=Dc-dc+12v+To+3.3v+5v+Buck+Step+Down+Power+Supply+Module+For+Arduino) |
| Wiring | 12–18 AWG, fuses | — | ~$10 | Load terminals → buck input |

### 7.2 Wiring

```
[Solar Panel] ──► [Renogy Wanderer 10A PWM]
                       │
                       ├── Battery + / -
                       │
                       └── LOAD terminals ──► [Buck 12V→3.3V/5V]
                                                    │
                                    ├── 5V → ESP32, Jetson (if 5V input)
                                    └── 3.3V → Sensors, LoRa
```

- **ESP32/MycoBrain:** 3.3V or 5V (via onboard regulator)
- **Jetson Nano:** 5V 4A recommended; check buck current capability (Jetson can draw 2–4A)
- **Jetson Orin NX:** Higher power; may need separate 12V→19V adapter or dedicated supply

---

## 8. MycoBrain Firmware Configuration per Tier

### 8.1 Device Roles (NVS / build flags)

| Tier | Device | `device_role` | Side B Flags |
|------|--------|---------------|--------------|
| 1 | Mushroom 1 | `mushroom1` | `ENABLE_WIFI=1`, `ENABLE_LORA=0` or `1` |
| 2 | Hyphae 1 | `hyphae1` | `ENABLE_LORA=1`, `ENABLE_WIFI=1` |
| 3 | Gateway | `gateway` | `ENABLE_LORA=1` (rx only), USB serial out |

### 8.2 Firmware Paths (mycobrain repo)

```
mycobrain/firmware/
├── side_a/          # Sensors, telemetry, commands
├── side_b/          # LoRa, WiFi, routing
├── gateway/         # LoRa RX → USB serial (ESP32 gateway, not Jetson)
└── MycoBrain_SideA/ # Legacy production (if used)
```

### 8.3 Build Commands

```bash
# Mushroom 1 (Side A + Side B)
cd mycobrain/firmware
pio run -e mycobrain-side-a -D DEVICE_ROLE=mushroom1
pio run -e mycobrain-side-b -D DEVICE_ROLE=mushroom1 -D ENABLE_WIFI=1

# Hyphae 1
pio run -e mycobrain-side-a -D DEVICE_ROLE=hyphae1
pio run -e mycobrain-side-b -D DEVICE_ROLE=hyphae1 -D ENABLE_LORA=1 -D ENABLE_WIFI=1

# Gateway (ESP32-based, if used alongside Jetson)
pio run -e mycobrain-gateway
```

---

## 9. Software Stack per Jetson

### 9.1 Tier 1 (Orin NX Super)

- **OS:** JetPack 5.x/6.x (Ubuntu 20.04/22.04)
- **MycoBrain integration:** USB serial (native Linux `/dev/ttyUSB*` or `/dev/ttyACM*`)
- **Optional:** Run `mycobrain_service_standalone.py` on Orin; or Orin runs Jetson server (camera, mic) and forwards serial to Server
- **Existing:** `mycosoft_mas/edge/jetson_server.py` (camera, audio, inference)

### 9.2 Tier 2 (Waveshare Nano/Xavier NX)

- **OS:** JetPack 4.6 / 5.x (Nano) or 5.x (Xavier NX)
- **Role:** Optional local processing; primarily uses Gateway for backhaul

### 9.3 Tier 3 (Jetson Nano Gateway)

- **OS:** JetPack 4.6
- **Software:**
  - LoRa module driver (SX1262 via SPI or USB module)
  - MDP parser (Python or C)
  - HTTP client to `http://192.168.0.188:8003/api/telemetry` or MAS ingestion API
- **Serial:** If MycoBrain USB connected: `pyserial`, read at 115200, parse MDP, forward

---

## 10. Step-by-Step Build Instructions

### Phase 1: Gateway (Jetson Nano B01)

1. Flash JetPack 4.6 to Jetson Nano.
2. Connect LoRa module (USB or SPI). Install driver/library (e.g. `pySX1262` or vendor SDK).
3. Clone MAS repo; copy MycoBrain MDP parser or use `mycobrain_service_standalone` in gateway mode.
4. Write bridge script: LoRa RX → parse MDP → POST to `http://192.168.0.188:8003/api/ingest/lora` (or equivalent).
5. Configure Ethernet/WiFi to reach 192.168.0.188.
6. Test: Hyphae 1 sends LoRa; Gateway receives and forwards.

### Phase 2: Mushroom 1 Direct (USB → PC → Server)

1. Build MycoBrain firmware for `mushroom1` (Side A + Side B).
2. Flash both MCUs. Connect MycoBrain USB (Side B or Side A) to PC.
3. On PC: Install MycoBrain service deps (`pip install -r requirements.txt`), set `MYCOBRAIN_SERIAL_PORT=COMx`, `MAS_REGISTRY_URL=http://192.168.0.188:8001`.
4. Run `mycobrain_service_standalone.py` (or `scripts/mycobrain-service.ps1 start`).
5. Verify: `curl http://localhost:8003/health` and `curl http://localhost:8003/devices`.
6. Server receives heartbeats at MAS 8001.

### Phase 3: Hyphae 1 via Gateway

1. Build MycoBrain firmware for `hyphae1` with LoRa + WiFi.
2. Flash both MCUs. Power Hyphae 1 (battery or Big Device buck).
3. Gateway: LoRa listener running, forwarding to Server.
4. Power Hyphae 1; verify telemetry at Server.
5. Optional: WiFi path if Hyphae 1 and Server on same LAN.

### Phase 4: Big Device Power (Optional)

1. Wire solar → Renogy Wanderer → battery.
2. Connect Load → buck converter → 5V/3.3V.
3. Power MycoBrain (3.3V or 5V) and/or Jetson (5V if current sufficient).
4. For Jetson Orin: Use separate 12V→19V supply if needed.

---

## 11. Testing and Verification

| Test | How |
|------|-----|
| Mushroom 1 serial | `pio device monitor -b 115200` on MycoBrain USB; see MDP telemetry |
| MycoBrain service | `curl http://localhost:8003/health`; `curl http://localhost:8003/devices` |
| MAS heartbeat | Check MAS logs or `GET /api/devices` on 192.168.0.188:8001 |
| Hyphae 1 LoRa | Gateway logs show received packets; Server shows device in registry |
| Gateway→Server | `curl http://192.168.0.188:8001/health` from Gateway |

---

## 12. BOM Summary

### Tier 1 — Mushroom 1
- Yahboom Jetson Orin NX Super (157 TOPS, 8/16GB) — ~$400–600
- MycoBrain (existing)
- USB-C cable — ~$5

### Tier 2 — Hyphae 1
- Waveshare Jetson Nano/Xavier NX Kit — ~$150–250
- MycoBrain (existing)
- LoRa SX1262 — ~$15
- 5V 4A power — ~$15

### Tier 3 — Gateway
- Jetson Nano B01 4GB — ~$99–150
- LoRa USB/SPI module — ~$25–40
- USB-UART (optional) — ~$5
- Ethernet cable — ~$5
- 5V 4A power — ~$15

### Big Device Power (Shared)
- Renogy Wanderer 10A PWM — ~$25
- 12V→3.3V/5V buck — ~$5
- Solar panel 12V — ~$30–60
- RITAR 12V battery — (existing)
- Wiring, fuses — ~$10

---

## Related Documents

- **Mycobrain repo:** `docs/FIRMWARE_ARCHITECTURE_FEB10_2026.md`, `legacy/MDP-Specifications.md`
- `docs/DEVICE_MANAGER_AND_GATEWAY_ARCHITECTURE_FEB10_2026.md` — Device manager and gateway architecture
- `docs/MYCOBRAIN_TO_MAS_FLOW_MAR07_2026.md` — MycoBrain→MAS heartbeat and device registry flow
- `docs/MYCA_FIRST_LIGHT_AND_SESSION_COMPLETE_FEB25_2026.md` — Jetson body, camera, audio, First Light
