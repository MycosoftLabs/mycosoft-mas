# Jetson + MycoBrain Production Deployment Guide

**Date:** March 13, 2026  
**Status:** Production reference  
**Related:** Production Jetson+MycoBrain plan, `JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md`, `EDGE_UNIFICATION_COMPLETE_MAR10_2026.md`

---

## Overview

This guide covers deploying production-ready **Mushroom 1** and **Hyphae 1** boxes: Side A firmware, Side B firmware, Jetson on-device operator, Jetson gateway router, flash procedure, and verification.

| Device | Jetson | Role |
|--------|--------|------|
| **Mushroom 1** | AGX Orin 32GB | On-device operator (full AI, multi-sensor) |
| **Hyphae 1** | Orin Nano Super 8GB | On-device operator (lightweight inference) |
| **Gateway** | Orin Nano 4GB | Gateway router (store-and-forward) |

---

## Bill of Materials (BOM)

### Mushroom 1 Box

| Item | Est. Cost |
|------|-----------|
| Jetson AGX Orin 32GB Developer Kit | $899 |
| NVMe SSD 256 GB | $35 |
| MycoBrain ESP32-S3 board | $15 |
| BME688 sensors x2 | $40 |
| FCI electrode array (4-channel) | $50 |
| LoRa SX1262 module | $15 |
| USB-C cable (Jetson ↔ ESP32) | $8 |
| Power supply (65W USB-C PD) | $25 |
| CSI camera module (optional) | $30 |
| Enclosure (3D printed, IP54) | $40 |
| Wiring, connectors, PCB | $25 |
| **Total** | **~$1,182** |

### Hyphae 1 Box

| Item | Est. Cost |
|------|-----------|
| Jetson Orin Nano Super 8GB Developer Kit | $275 |
| MicroSD 128 GB / NVMe 128 GB | $25 |
| MycoBrain ESP32-S3 board | $15 |
| BME688 sensors x2 | $40 |
| Soil moisture ADC (hyphae1 role) | $5 |
| LoRa SX1262 module | $15 |
| USB-C cable | $8 |
| Power supply (25W USB-C PD) | $20 |
| Enclosure | $30 |
| Wiring, connectors | $20 |
| **Total** | **~$453** |

### Gateway Jetson (4GB)

| Item | Est. Cost |
|------|-----------|
| Jetson Orin Nano 4GB Developer Kit | ~$199 |
| MycoBrain ESP32-S3 board | $15 |
| LoRa SX1262 module | $15 |
| USB-C cable | $8 |
| Power supply | $20 |
| **Total** | **~$257** |

---

## Wiring Diagram

### Side A ↔ Side B ↔ Jetson

```
Side A (ESP32-S3)          Side B (ESP32-S3)           Jetson
─────────────────          ─────────────────           ──────
UART1 TX (GPIO17) ────────► UART_RX (Side B) ──────────► /dev/ttyUSB0 (Jetson UART)
UART1 RX (GPIO18) ◄──────── UART_TX (Side B) ◄────────── Jetson UART TX

Side B UART2 ◄────────────► Side A (UART pass-through)
```

- **Side A** runs sensor acquisition (BME688 x2, soil moisture for hyphae1); sends MDP frames to Side B.
- **Side B** bridges Side A ↔ Jetson; passes MDP frames bidirectionally.
- **Jetson** connects to Side B via USB-C serial (`/dev/ttyUSB0` or `/dev/ttyACM0`). Second serial for Side A direct if using split topology.

### Pin Reference (Side A)

| Function | GPIO | Notes |
|----------|------|-------|
| BME688 AMB (I2C) | 5 (SDA), 4 (SCL) | Addr 0x77 |
| BME688 ENV (I2C) | 5 (SDA), 4 (SCL) | Addr 0x76 |
| Soil moisture ADC | 1 (hyphae1) | Capacitive sensor |
| NeoPixel | 15 | RGB status |
| Piezo | 46 | Buzzer |
| UART1 TX/RX | 17, 18 | To Side B |

### Pin Reference (Side B)

| Function | GPIO | Notes |
|----------|------|-------|
| UART1 TX/RX | To Jetson | USB serial bridge |
| UART2 TX/RX | To Side A | MDP frame pass-through |

---

## Flash Procedure

### Prerequisites

- **PlatformIO** (`pip install platformio` or VS Code PlatformIO extension)
- USB drivers for ESP32-S3 (CP210x/CH340)
- COM port access (Windows: COM7, COM8; Linux: `/dev/ttyUSB*`)

### Step 1: Flash Side A First

```powershell
# Mushroom 1 (dual BME688, no soil)
.\scripts\flash-mycobrain-production.ps1 -Board SideA -Role mushroom1 -Port COM7

# Hyphae 1 (dual BME688 + soil moisture)
.\scripts\flash-mycobrain-production.ps1 -Board SideA -Role hyphae1 -Port COM7
```

### Step 2: Flash Side B

```powershell
.\scripts\flash-mycobrain-production.ps1 -Board SideB -Port COM8
```

Side B has no role (single build). Ensure COM8 is the Side B board.

### Flash Script Options

| Parameter | Values | Required |
|-----------|--------|----------|
| `-Board` | `SideA`, `SideB` | Yes |
| `-Role` | `mushroom1`, `hyphae1` | Side A only (default: mushroom1) |
| `-Port` | `COM3`, `COM7`, etc. | No (auto-detect) |

---

## Jetson Setup Procedure

### On-Device Jetson (Mushroom 1 / Hyphae 1)

1. **Copy MAS repo** to Jetson (scp, git clone, or USB).
2. **Run install script:**
   ```bash
   cd /path/to/mycosoft-mas
   ./deploy/jetson-ondevice/install.sh
   ```
3. **Edit env** for role and serial ports:
   ```bash
   sudo nano /etc/mycobrain/operator.env
   ```
   Use `env.mushroom1` or `env.hyphae1` as template. Set:
   - `ONDEVICE_ROLE=mushroom1` or `hyphae1`
   - `SERIAL_SIDE_A=/dev/ttyUSB0` (or `ttyACM0`)
   - `SERIAL_SIDE_B=/dev/ttyUSB1` (or as discovered)
   - `MAS_API_URL=http://192.168.0.188:8001`
   - `NLM_API_URL`, `MINDEX_API_URL` if used
4. **Restart service:**
   ```bash
   sudo systemctl restart mycobrain-operator
   ```

### Gateway Jetson

1. Copy MAS repo to Jetson.
2. Run install:
   ```bash
   ./deploy/jetson-gateway/install.sh
   ```
3. Edit `/etc/mycobrain/gateway.env` from `env.gateway` template.
4. Restart:
   ```bash
   sudo systemctl restart mycobrain-gateway
   ```

### Systemd Units

| Service | Unit File | Port | Purpose |
|---------|-----------|------|---------|
| On-Device Operator | `mycobrain-operator.service` | 8080 | MDP bridge, telemetry pipeline, NLM/MINDEX push |
| Gateway Router | `mycobrain-gateway.service` | 8003 | Store-and-forward, upstream publish, self-heartbeat |

---

## Verification Checklist

### Firmware

- [ ] Side A: HELLO frame with correct `role` (mushroom1/hyphae1) and `fw_version: side-a-mdp-2.0.0`
- [ ] Side B: Heartbeat frames every 5s with `fw_version: side-b-mdp-2.0.0`
- [ ] Telemetry frames contain BME688 data (temp, humidity, pressure, IAQ for mushroom1; + soil_moisture for hyphae1)

### On-Device Operator

- [ ] Health: `curl http://<jetson-ip>:8080/health` returns 200
- [ ] Telemetry latest: `curl http://<jetson-ip>:8080/telemetry/latest` returns JSON array
- [ ] Telemetry stream: `curl -N http://<jetson-ip>:8080/telemetry/stream` shows SSE events
- [ ] MAS registry: Device appears in `GET /api/devices/network` with status online
- [ ] NLM translate: Telemetry reaches NLM `/api/translate` (check MAS logs)
- [ ] MINDEX FCI: Telemetry reaches MINDEX `/api/fci/telemetry` (if configured)

### Gateway Router

- [ ] Health: `curl http://<gateway-ip>:8003/health` returns 200
- [ ] Devices: `curl http://<gateway-ip>:8003/devices` lists ingested device IDs
- [ ] Self-heartbeat: Gateway appears in MAS registry every 30s

### Website

- [ ] Device detail page: `/natureos/devices/<deviceId>` shows identity, telemetry, command panel
- [ ] Live telemetry card: Polls every 5s, displays sensor readings
- [ ] Command panel: Read sensors, beep, LED, e-stop (admin required)
- [ ] Network page: Device cards link to "View Details" → detail page

---

## File Reference

| Category | Path |
|----------|------|
| Shared MDP lib | `firmware/common_mdp/mdp_codec.h` |
| Side A firmware | `firmware/MycoBrain_SideA_MDP/` |
| Side B firmware | `firmware/MycoBrain_SideB_MDP/` |
| Telemetry pipeline | `mycosoft_mas/edge/telemetry_pipeline.py` |
| On-device operator | `mycosoft_mas/edge/ondevice_operator.py` |
| Gateway router | `mycosoft_mas/edge/gateway_router.py` |
| On-device deploy | `deploy/jetson-ondevice/` |
| Gateway deploy | `deploy/jetson-gateway/` |
| Flash script | `scripts/flash-mycobrain-production.ps1` |
| Device configs | `WEBSITE/website/lib/device-configs.ts` |
| Device detail page | `WEBSITE/website/app/natureos/devices/[deviceId]/page.tsx` |

---

## Related Documentation

- `docs/JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md` — Hardware spec, BOM, architecture
- `docs/EDGE_UNIFICATION_COMPLETE_MAR10_2026.md` — Edge runtime, CREP presence, telemetry
- `docs/INTEGRATION_CONTRACTS_CANONICAL_MAR10_2026.md` — Jetson/MycoBrain edge contract
- `docs/MYCOBRAIN_GATEWAY_NODE_RECOGNITION_MAR13_2026.md` — Gateway recognition, serial allowlist
