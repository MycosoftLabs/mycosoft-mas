# Device Manager and Gateway Architecture

**Date**: February 10, 2026  
**Author**: MYCA  
**Status**: Complete

## Overview

MycoBrain devices are visible across the entire network via the MAS Device Registry. A PC running the MycoBrain service acts as a gateway: it ingests devices over **serial** (e.g. COM7), and optionally over **LoRa**, **Bluetooth**, and **WiFi** in the future. All devices register with MAS via heartbeat; the website (local or sandbox) shows them in the Device Manager (Local + Network tabs).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Field / Lab                                                                │
│  MycoBrain (serial)  MycoBrain (LoRa)  MycoBrain (BT)  MycoBrain (WiFi)      │
└───────────┬───────────────┬───────────────┬───────────────┬───────────────┘
            │ serial         │ radio         │ radio         │ radio
            ▼                ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Gateway PC (this machine or server-adjacent gateway)                       │
│  MycoBrain Service (port 8003)                                              │
│  - Serial ingestion (COM7, etc.)                                            │
│  - Future: LoRa / Bluetooth / WiFi ingestion                               │
│  - Heartbeat → MAS Device Registry                                          │
└───────────────────────────────────────────┬───────────────────────────────────┘
                                            │ HTTP POST /api/devices/register
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  MAS (192.168.0.188:8001)                                                   │
│  Device Registry: /api/devices (list), /api/devices/{id}/command (proxy)     │
│  Stores: device_id, host, port, ingestion_source (serial|lora|bluetooth|    │
│          wifi|gateway), last_seen, etc.                                     │
└───────────────────────────────────────────┬───────────────────────────────────┘
                                            │ GET /api/devices, POST command
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Website (localhost:3010 or sandbox.mycosoft.com:3000)                      │
│  Device Manager: Local tab (MycoBrain service on this host),                 │
│                  Network tab (all devices from MAS registry)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Serial (current)

1. MycoBrain board on **COM7** → MycoBrain service (localhost:8003) on this PC.
2. Service connects device as `mycobrain-COM7`, then sends heartbeat to MAS:
   - `POST http://192.168.0.188:8001/api/devices/register`
   - Body: `device_id`, `device_name`, `host` (this PC’s LAN IP, e.g. 192.168.0.172), `port` (8003), `ingestion_source: "serial"`, etc.
3. MAS stores the device; any client can call `GET /api/devices` (or website `GET /api/devices/network`) and see it.
4. Commands: Website → MAS `POST /api/devices/{device_id}/command` → MAS proxies to `http://<host>:8003/devices/{device_id}/command`.

### Future: LoRa / Bluetooth / WiFi

- Same registry and heartbeat format.
- Gateway service (or a dedicated radio-ingestion process) will send heartbeats with `ingestion_source`: `"lora"`, `"bluetooth"`, or `"wifi"`.
- Device Manager can show ingestion source (Serial / LoRa / BT / WiFi) for each device.

## Key Components

| Component | Location | Purpose |
|----------|----------|---------|
| Device Registry API | `mycosoft_mas/core/routers/device_registry_api.py` | Register, list, command proxy, telemetry |
| MycoBrain service | `services/mycobrain/mycobrain_service_standalone.py` | Serial ingestion, heartbeat to MAS |
| Website devices API | `app/api/devices/route.ts`, `app/api/devices/network/route.ts` | Local + network device list, discovery |
| Network command | `app/api/devices/network/[deviceId]/command/route.ts` | Send command to network device via MAS |

## Device Registry Fields

- `device_id`, `device_name`, `host`, `port`
- `ingestion_source`: `"serial"` | `"lora"` | `"bluetooth"` | `"wifi"` | `"gateway"`
- `connection_type`: `"lan"` | `"tailscale"` | `"cloudflare"`
- `last_seen`, `registered_at`, `status` (online/stale/offline)

## Making COM7 Visible to the Entire Network

1. **Run MycoBrain service on this PC** (with board on COM7):
   - `python services/mycobrain/mycobrain_service_standalone.py`
   - Ensure `MAS_REGISTRY_URL=http://192.168.0.188:8001` (or set in env).
2. **Deploy MAS** on 192.168.0.188 with the latest `device_registry_api.py` (list at both `/api/devices` and `/api/devices/`, plus `ingestion_source` support).
3. **Verify**: From any machine (e.g. sandbox or another PC), open Device Manager → Network tab; the device should appear. Send a command from the Network tab; MAS will proxy to `http://<this_PC_IP>:8003/devices/mycobrain-COM7/command`.

## Related Documents

- [MYCOBRAIN_BETO_SETUP_GUIDE_FEB09_2026.md](./MYCOBRAIN_BETO_SETUP_GUIDE_FEB09_2026.md)
- [TAILSCALE_REMOTE_DEVICE_GUIDE_FEB09_2026.md](./TAILSCALE_REMOTE_DEVICE_GUIDE_FEB09_2026.md)
- [VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md)
