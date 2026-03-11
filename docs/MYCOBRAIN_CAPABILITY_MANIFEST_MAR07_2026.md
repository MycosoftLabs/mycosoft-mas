# MycoBrain Capability Manifest

**Date:** March 7, 2026  
**Status:** Current  
**Related:** MycoBrain Rail Unification, device registry, heartbeat

## Overview

The **capability manifest** is the canonical contract for device sensors and capabilities. It maps device role (reported by firmware in hello/status) to sensor and capability lists. This flows:

1. **Firmware** → reports `role` in hello (e.g. `side-a`, `mushroom1`)
2. **MycoBrain Service** → uses manifest to derive `sensors` and `capabilities` for heartbeat
3. **MAS** → stores and returns them in device registry
4. **Website** → displays via `/api/devices/network`; uses `CAPABILITY_DISPLAY` / `SENSOR_DISPLAY` for labels

## Source of Truth

| Location | Purpose |
|----------|---------|
| `mycosoft_mas/devices/capability_manifest.py` | MAS package (API, orchestration) |
| `services/mycobrain/capability_manifest.py` | MycoBrain standalone service (mirror) |

**Keep both in sync** when adding new roles or capabilities.

## Manifest Entries

| Role | Sensors | Capabilities |
|------|---------|--------------|
| `side-a` | bme688_a, bme688_b | led, buzzer, i2c, neopixel |
| `side-a-working` | (none) | led, buzzer, i2c |
| `mushroom1` | bme688_a, bme688_b | led, buzzer, i2c, neopixel, telemetry |
| `sporebase` | bme688, spore_detection | led, buzzer, i2c, telemetry |
| `hyphae1` | bme688, soil_moisture | led, i2c, telemetry |
| `alarm` | bme688, sound | led, buzzer, telemetry |
| `gateway` | (none) | service, serial, lora, bluetooth, wifi |
| `standalone` | bme688_a, bme688_b | led, buzzer, i2c |

Unknown roles default to `standalone` manifest.

## Website Display Labels

`WEBSITE/website/lib/device-products.ts` exports:

- `CAPABILITY_DISPLAY` — human-readable names for capability codes
- `SENSOR_DISPLAY` — human-readable names for sensor codes

Use when rendering device cards or details.

## Maintenance

1. **Add new role:** Add entry to both manifest files, then update this doc.
2. **Add sensor/capability:** Add to role manifest and to display maps in device-products.ts.
