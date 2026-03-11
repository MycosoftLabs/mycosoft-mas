# MycoBrain Firmware Baseline Rebaseline

**Date**: March 7, 2026  
**Author**: MYCA  
**Status**: Complete  
**Related Plan**: Jetson-Backed MycoBrain Field Architecture

## Overview

This document establishes the canonical firmware baseline for the MycoBrain field architecture. It rebaselines documentation around DeviceManager/DualMode as current operational truth, SideA/SideB as the target split architecture, and MycoBrain_Working as recovery-only.

## Canonical Firmware Landscape

### 1. Operational Baseline (Current Reality)

**Firmware**: DeviceManager / DualMode lineage  
**Location**: `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`  
**Identifiers**: FW_NAME `mycobrain.sideA.dualmode`, FW_VERSION `1.1.0`

This is the **operational baseline** — what is or has been running on COM7 and in production. It accepts:
- CLI commands: `status`, `help`, `scan`, `led rgb`, `coin`, `bump`, `power`, `1up`, `morgio`, etc.
- JSON commands: `{"cmd":"status"}`, `{"type":"cmd","op":"status"}`, etc.

**Features**:
- BME688 environmental sensors (2x)
- I2C bus scanning
- NeoPixel (SK6805 on GPIO15)
- Buzzer (GPIO16)
- MOSFET outputs (GPIO12/13/14)
- Machine Mode (NDJSON output)
- Output format modes: JSON, lines

**PlatformIO variant**: `firmware/MycoBrain_DualMode_PIO/src/main.cpp` — simpler dualmode with hello, status, telemetry, led, buzzer; identifier `dualmode-pio`.

### 2. Target Split Architecture Baseline

**Side A (Sensing/Control)**  
**Location**: `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`

Owns:
- Sensing (BME688, I2C, analog inputs)
- Local peripheral control
- Actuation primitives (MOSFETs, NeoPixel, Buzzer)
- Authoritative device identity origin
- Telemetry and NDJSON machine mode

This is the **target sensing/control firmware** for the two-Jetson architecture.

**Side B (Transport)**  
**Location**: `firmware/MycoBrain_SideB/MycoBrain_SideB.ino`

Owns:
- UART relay to Side A
- PC ↔ Side A passthrough
- Command routing and telemetry forwarding

**Gap**: Side B does not yet implement LoRa/BLE/WiFi/SIM transport. The two-Jetson plan defines Side B as transport-only; LoRa/BLE/WiFi/SIM are future work.

### 3. Recovery-Only Firmware

**Firmware**: MycoBrain_Working  
**Location**: `firmware/MycoBrain_Working/src/main.cpp`

Minimal firmware (~158 lines):
- Hello, I2C scan, telemetry, LED, buzzer
- No BME688, no full command set, no Machine Mode

**Use**: Recovery only — when boards fail to boot with production firmware, flash this minimal build to restore serial and basic I/O. Do **not** use as production baseline.

### 4. Experimental Reference (Mine, Not Baseline)

**Firmware**: MycoBrain_ScienceComms  
**Location**: `firmware/MycoBrain_ScienceComms/`  
**Docs**: `firmware/MycoBrain_ScienceComms/docs/COMMANDS.md`

Experimental modem/stimulus/comms surface. **Mine for patterns** — modem commands, stimulus protocols, comms framing — but **do not use as baseline**. ScienceComms has caused boot loops in the past; treat as reference only.

## Mapping to Plan Phases

| Phase | Firmware | Role |
|-------|----------|------|
| Phase 1 (Architecture) | — | Protocol unification |
| Phase 2 (Jetson 16GB) | — | Edge operator runtime |
| Phase 3 (Side A refactor) | MycoBrain_SideA | Align to deterministic MDP |
| Phase 4 (Side B refactor) | MycoBrain_SideB | Transport executor only |
| Phase 5 (Gateway) | — | 4GB Jetson + LilyGO |
| Phase 6 (Stack/UI) | — | Registry, device network |

## Summary Table

| Firmware | Role | Use |
|----------|------|-----|
| MycoBrain_DeviceManager | Operational baseline | Current COM7 / production |
| MycoBrain_DualMode_PIO | Operational (PIO) | Alternative build |
| MycoBrain_SideA | Target sensing/control | Future split architecture |
| MycoBrain_SideB | Target transport | Future split architecture |
| MycoBrain_Working | Recovery only | Minimal boot recovery |
| MycoBrain_ScienceComms | Experimental reference | Mine for modem/comms patterns |

## Related Documents

- [Jetson-Backed MycoBrain Field Architecture](.cursor/plans/jetson-backed_mycobrain_field_architecture_c1b2baea.plan.md) (plan)
- [SIDE_B_TRANSPORT_AND_BACKHAUL_MAR07_2026.md](./SIDE_B_TRANSPORT_AND_BACKHAUL_MAR07_2026.md)
- [MYCOBRAIN_JETSON_GATEWAY_BUILD_PLAN_MAR07_2026.md](./MYCOBRAIN_JETSON_GATEWAY_BUILD_PLAN_MAR07_2026.md)
- [MYCOBRAIN_RAIL_UNIFICATION_COMPLETE_MAR07_2026.md](./MYCOBRAIN_RAIL_UNIFICATION_COMPLETE_MAR07_2026.md)
- [firmware/MYCOBRAIN_README.md](../firmware/MYCOBRAIN_README.md)
- [firmware/README.md](../firmware/README.md)
