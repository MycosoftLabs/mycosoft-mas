# Jetson + MycoBrain Hardware Plan

**Date:** March 9, 2026
**Author:** MYCA Coding Agent
**Status:** Draft — Pending CEO Approval

---

## Overview

Two MycoBrain + Jetson configurations sharing the same architecture but at different performance tiers:

| Device | Jetson Module | Budget | Role |
|--------|--------------|--------|------|
| **Mushroom 1** | Jetson AGX Orin 32GB | ~$1,200 | Primary fungal biocomputer — full AI inference, multi-sensor fusion, FCI processing |
| **Hyphae 1** | Jetson Orin Nano Super 8GB | ~$275 | Edge sensor node — lightweight inference, environmental monitoring, mesh relay |

Both devices pair a Jetson (AI compute) with an ESP32-S3 MycoBrain board (sensor I/O, LoRa, bioelectric interface). The Jetson handles inference and orchestration; the ESP32 handles real-time sensor acquisition and radio.

---

## Architecture: Shared Design

```
┌─────────────────────────────────────────────────────┐
│                   Jetson Module                      │
│  ┌───────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ AI Engine │  │ Container│  │  MAS Agent        │  │
│  │ (TensorRT)│  │ Runtime  │  │  (FastAPI + WS)   │  │
│  └─────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│        │              │                  │            │
│        └──────────────┼──────────────────┘            │
│                       │                               │
│              USB-C / UART Serial                      │
│              (115200 baud, MDP v1)                    │
└───────────────────────┬───────────────────────────────┘
                        │
┌───────────────────────┴───────────────────────────────┐
│                ESP32-S3 MycoBrain Board                │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌────────┐  │
│  │ BME688   │  │ BME688   │  │  FCI   │  │  LoRa  │  │
│  │ AMB 0x77 │  │ ENV 0x76 │  │ Driver │  │ SX1262 │  │
│  └──────────┘  └──────────┘  └────────┘  └────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌────────┐              │
│  │ NeoPixel │  │  Piezo   │  │  BLE   │              │
│  │ GPIO 15  │  │ GPIO 46  │  │        │              │
│  └──────────┘  └──────────┘  └────────┘              │
└───────────────────────────────────────────────────────┘
```

**Communication flow:**
1. ESP32 acquires sensor data at hardware speed (I2C, ADC, SPI)
2. ESP32 sends telemetry to Jetson via USB serial (MDP v1 protocol, COBS framing, CRC16)
3. Jetson runs AI inference on fused sensor data (TensorRT)
4. Jetson reports to MAS Orchestrator (192.168.0.188:8001) over WiFi/Ethernet
5. Both devices register via `POST /api/registry/devices` and heartbeat via `POST /api/devices/heartbeat`

---

## Mushroom 1 — Full Specification

### Jetson AGX Orin 32GB (~$1,200)

| Spec | Value |
|------|-------|
| **Module** | NVIDIA Jetson AGX Orin 32GB |
| **GPU** | 2048-core NVIDIA Ampere, 64 Tensor Cores |
| **CPU** | 12-core Arm Cortex-A78AE |
| **AI Performance** | 200 TOPS (INT8) |
| **Memory** | 32 GB LPDDR5, 204.8 GB/s bandwidth |
| **Storage** | 64 GB eMMC + NVMe SSD (256 GB recommended) |
| **Power** | 15W–60W configurable |
| **Connectivity** | 10GbE, WiFi 6, USB 3.2, PCIe Gen4, HDMI |
| **OS** | JetPack 6.x (Ubuntu 22.04 + CUDA 12 + TensorRT) |

### MycoBrain Board (ESP32-S3)

| Component | Detail |
|-----------|--------|
| **MCU** | ESP32-S3, 8 MB PSRAM, 16 MB Flash |
| **Sensor 1** | BME688 (AMB) — I2C 0x77, GPIO5/4 |
| **Sensor 2** | BME688 (ENV) — I2C 0x76, solder bridge mod |
| **Bioelectric** | FCI driver — 4-channel, 1 kHz sample rate |
| **Radio** | LoRa SX1262 + WiFi + BLE |
| **Indicators** | NeoPixel RGB (GPIO 15), Piezo (GPIO 46) |
| **Connection** | USB-C to Jetson (UART 115200) |

### Mushroom 1 Capabilities

- **On-device LLM inference** — Run 7B–13B parameter models locally (Llama 3, Mistral) via TensorRT-LLM
- **Real-time bioelectric analysis** — FCI signal classification at 1 kHz, pattern matching against 9 GFST signal types
- **Multi-sensor fusion** — Combine BME688 dual readings + bioelectric + LoRa mesh data
- **Edge AI vision** — CSI camera support for mushroom growth monitoring, morphology tracking
- **Local MAS agent** — Full FastAPI service running MycoBrainDeviceAgent + inference pipeline
- **LoRa mesh coordinator** — Acts as LoRa gateway for nearby Hyphae nodes
- **NVIDIA Earth2 edge inference** — Weather/climate model inference for grow environment optimization

### Mushroom 1 Software Stack

```
JetPack 6.x (Ubuntu 22.04)
├── Docker (MAS agent container)
│   ├── FastAPI service (port 8003)
│   ├── MycoBrainDeviceAgent (v1)
│   ├── BME688SensorAgent (v2)
│   ├── FCI signal processor
│   └── WebSocket bridge to ESP32
├── TensorRT-LLM (local inference)
├── NVIDIA Triton Inference Server
├── Jetson Inference (vision AI)
└── Tailscale (mesh VPN to MAS network)
```

### Mushroom 1 BOM (Bill of Materials)

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

---

## Hyphae 1 — Full Specification

### Jetson Orin Nano Super 8GB (~$275)

| Spec | Value |
|------|-------|
| **Module** | NVIDIA Jetson Orin Nano Super 8GB |
| **GPU** | 1024-core NVIDIA Ampere, 32 Tensor Cores |
| **CPU** | 6-core Arm Cortex-A78AE |
| **AI Performance** | 67 TOPS (INT8) |
| **Memory** | 8 GB LPDDR5, 102 GB/s bandwidth |
| **Storage** | MicroSD + NVMe M.2 (128 GB recommended) |
| **Power** | 7W–25W configurable |
| **Connectivity** | GbE, WiFi, USB 3.2, PCIe Gen3 |
| **OS** | JetPack 6.x (Ubuntu 22.04 + CUDA 12 + TensorRT) |

### MycoBrain Board (ESP32-S3) — Same as Mushroom 1

| Component | Detail |
|-----------|--------|
| **MCU** | ESP32-S3, 8 MB PSRAM, 16 MB Flash |
| **Sensor 1** | BME688 (AMB) — I2C 0x77 |
| **Sensor 2** | BME688 (ENV) — I2C 0x76, solder bridge mod |
| **Bioelectric** | FCI driver — 4-channel, 1 kHz sample rate |
| **Radio** | LoRa SX1262 + WiFi + BLE |
| **Indicators** | NeoPixel RGB (GPIO 15), Piezo (GPIO 46) |
| **Connection** | USB-C to Jetson (UART 115200) |

### Hyphae 1 Capabilities

- **Lightweight edge inference** — Run quantized models up to 3B–8B parameters (TinyLlama, Phi-3-mini)
- **Environmental monitoring** — Continuous BME688 dual-sensor air quality and climate tracking
- **Bioelectric sensing** — FCI signal capture and basic pattern classification
- **LoRa mesh node** — Relay sensor data to Mushroom 1 or directly to MAS
- **Anomaly detection** — TensorRT-optimized anomaly models for environmental alerts
- **Low-power operation** — 7W idle mode for solar/battery deployments
- **Mesh telemetry forwarding** — Aggregate and relay data from simpler LoRa-only nodes

### Hyphae 1 Software Stack

```
JetPack 6.x (Ubuntu 22.04)
├── Docker (MAS agent container, lightweight)
│   ├── FastAPI service (port 8003)
│   ├── MycoBrainDeviceAgent (v1)
│   ├── BME688SensorAgent (v2)
│   ├── FCI signal processor (lite)
│   └── WebSocket bridge to ESP32
├── TensorRT (optimized inference, quantized models)
├── Jetson Inference (edge vision, optional)
└── Tailscale (mesh VPN to MAS network)
```

### Hyphae 1 BOM (Bill of Materials)

| Item | Est. Cost |
|------|-----------|
| Jetson Orin Nano Super Dev Kit | $249 |
| MicroSD 128 GB (A2 speed) | $15 |
| MycoBrain ESP32-S3 board | $15 |
| BME688 sensors x2 | $40 |
| FCI electrode array (4-channel) | $50 |
| LoRa SX1262 module | $15 |
| USB-C cable (Jetson ↔ ESP32) | $8 |
| Power supply (25W USB-C) | $15 |
| Enclosure (3D printed, IP54) | $30 |
| Wiring, connectors, PCB | $15 |
| **Total** | **~$452** |

> **Note:** The $275 covers the Jetson itself. Full node cost is ~$452 with sensors. If budget is strictly $275 total, the FCI array and one BME688 can be deferred (reducing to ~$295).

---

## Comparison: Mushroom 1 vs Hyphae 1

| Feature | Mushroom 1 (AGX Orin 32GB) | Hyphae 1 (Orin Nano Super) |
|---------|---------------------------|---------------------------|
| **AI Performance** | 200 TOPS | 67 TOPS |
| **Memory** | 32 GB LPDDR5 | 8 GB LPDDR5 |
| **Local LLM** | 7B–13B models | 3B–8B models (quantized) |
| **Power Draw** | 15–60W | 7–25W |
| **Vision AI** | Yes (CSI camera) | Optional |
| **LoRa Role** | Gateway/Coordinator | Node/Relay |
| **Sensors** | Dual BME688 + FCI | Dual BME688 + FCI |
| **MAS Agent** | Full orchestrator | Lightweight agent |
| **Triton Server** | Yes | No (TensorRT only) |
| **Use Case** | Central hub, inference, coordination | Edge node, monitoring, relay |
| **Jetson Cost** | ~$899 | ~$249 |
| **Total Node Cost** | ~$1,182 | ~$452 |

---

## Network Topology

```
                    MAS Orchestrator (192.168.0.188:8001)
                              │
                    ┌─────────┴─────────┐
                    │  WiFi / Ethernet   │
                    │  (Tailscale VPN)   │
                    │                    │
            ┌───────┴───────┐    ┌───────┴───────┐
            │  Mushroom 1   │    │   Hyphae 1    │
            │  AGX Orin 32G │    │  Orin Nano 8G │
            │  200 TOPS     │    │  67 TOPS      │
            │  port 8003    │    │  port 8003    │
            └───────┬───────┘    └───────┬───────┘
                    │ USB-C              │ USB-C
            ┌───────┴───────┐    ┌───────┴───────┐
            │  MycoBrain    │    │  MycoBrain    │
            │  ESP32-S3     │    │  ESP32-S3     │
            │  2x BME688    │◄──►│  2x BME688    │
            │  FCI + LoRa   │LoRa│  FCI + LoRa   │
            └───────────────┘    └───────────────┘
```

**Data flow:**
1. ESP32 → Jetson: Raw sensor telemetry via USB serial (MDP v1)
2. Jetson: AI inference, pattern classification, anomaly detection
3. Jetson → MAS: Processed insights via REST/WebSocket to Orchestrator
4. Hyphae ↔ Mushroom: LoRa mesh for low-power inter-device comms
5. MAS → Jetson: Task assignments, model updates, configuration pushes

---

## MAS Integration

### Device Registration

Both devices register with the MAS Orchestrator at startup:

```json
POST http://192.168.0.188:8001/api/registry/devices
{
  "device_id": "mushroom1-001",
  "device_type": "mushroom1",
  "hardware": {
    "jetson": "agx_orin_32gb",
    "esp32": "mycobrain_v1",
    "sensors": ["bme688_amb", "bme688_env", "fci_4ch"],
    "radios": ["wifi6", "lora_sx1262", "ble5"]
  },
  "capabilities": ["inference", "sensor_fusion", "lora_gateway", "bioelectric"],
  "endpoints": {
    "api": "http://<device_ip>:8003",
    "ws": "ws://<device_ip>:8003/ws"
  }
}
```

### Agent Mapping

| MAS Agent | Runs On | Purpose |
|-----------|---------|---------|
| MycoBrainCoordinator | MAS VM (188) | Fleet management of all Jetson+MycoBrain nodes |
| MycoBrainDeviceAgent | Each Jetson | Local device control and telemetry |
| BME688SensorAgent | Each Jetson | Environmental sensor management |
| FirmwareAgent | Each Jetson | OTA updates for paired ESP32 |
| LoRaGatewayAgent | Mushroom 1 | LoRa mesh coordination |

### Memory Integration

| Layer | Mushroom 1 | Hyphae 1 |
|-------|-----------|----------|
| Ephemeral (30 min) | Local sensor buffer | Local sensor buffer |
| Session (24 hr) | Redis on MINDEX (189) | Redis on MINDEX (189) |
| Working (7 days) | Redis on MINDEX (189) | Redis on MINDEX (189) |
| Semantic (permanent) | Postgres + Qdrant (189) | Postgres + Qdrant (189) |
| Episodic (permanent) | Postgres (189) | Postgres (189) |

---

## Deployment Phases

### Phase 1: Jetson Setup (Week 1)
- Flash JetPack 6.x on both Jetsons
- Install Docker, Tailscale, NVIDIA Container Runtime
- Verify GPU inference with TensorRT benchmark
- Connect to MAS Tailscale mesh network

### Phase 2: MycoBrain Integration (Week 2)
- Flash ESP32-S3 firmware (`firmware/MycoBrain_DeviceManager/`)
- Wire dual BME688 sensors (verify I2C 0x77 + 0x76)
- Wire FCI electrode array
- Connect ESP32 to Jetson via USB-C
- Verify MDP v1 serial communication

### Phase 3: MAS Agent Deployment (Week 3)
- Deploy MAS agent Docker container to each Jetson
- Register devices with Orchestrator
- Verify telemetry flow: ESP32 → Jetson → MAS → MINDEX
- Test LoRa mesh between Mushroom 1 and Hyphae 1
- Validate heartbeat and health monitoring

### Phase 4: AI Model Deployment (Week 4)
- Deploy TensorRT-optimized models to Mushroom 1
- Deploy quantized edge models to Hyphae 1
- Test bioelectric pattern classification (9 GFST patterns)
- Test environmental anomaly detection
- Benchmark inference latency and power consumption

---

## Power & Thermal

| Device | Idle | Active | Peak | Recommended PSU |
|--------|------|--------|------|----------------|
| Mushroom 1 (Jetson + ESP32) | ~18W | ~40W | ~65W | 65W USB-C PD |
| Hyphae 1 (Jetson + ESP32) | ~9W | ~20W | ~28W | 25W USB-C |

**Thermal management:**
- Mushroom 1: Active fan cooling (included with AGX Orin dev kit)
- Hyphae 1: Passive heatsink sufficient at 25W mode; fan recommended for sustained inference

**Solar viability (Hyphae 1 only):**
- 7W idle mode + 100W solar panel + 50Wh battery = ~8 hrs autonomous operation
- Suitable for outdoor field deployment

---

## Future Expansion

- **Mushroom 2+**: Additional AGX Orin nodes for multi-zone coverage
- **Hyphae 2–N**: Orin Nano mesh network scaling (10+ nodes per Mushroom hub)
- **SporeBase integration**: Airborne spore collector feeding into Mushroom 1 AI pipeline
- **TruffleBot coordination**: Mushroom 1 as inference server for autonomous sampling robot
- **PetraeusDevice link**: Lab HDMEA data streamed to Mushroom 1 for real-time analysis
- **GPU VM offload**: Heavy training workloads forwarded to GPU VM (192.168.0.190)

---

## References

- [NVIDIA Jetson AGX Orin](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)
- [NVIDIA Jetson Orin Nano Super Dev Kit](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/)
- [Jetson Developer Kits](https://developer.nvidia.com/embedded/jetson-developer-kits)
- Existing codebase: `mycosoft_mas/devices/mushroom1.py`, `mycosoft_mas/devices/base.py`
- Existing firmware: `firmware/MycoBrain_DeviceManager/`
- Sensor docs: `docs/BME688_DUAL_SENSOR_SETUP.md`
