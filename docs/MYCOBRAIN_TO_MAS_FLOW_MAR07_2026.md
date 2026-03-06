# MycoBrain to MAS Device Flow — March 7, 2026

**Status:** Documentation  
**Purpose:** Document how MycoBrain devices register with MAS and how MYCA can query device status.  
**Related:** `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md`

---

## Overview

MycoBrain hardware (ESP32 boards, sensors) connects via:

1. **MycoBrain Service** (port 8003) — Serial comms, local device management
2. **MAS Device Registry** — Heartbeats from service to MAS
3. **Website Device Manager** — Fetches from MAS `/api/devices/network`

## Flow

```
MycoBrain HW (USB serial)
    ↓
MycoBrain Service (localhost:8003 or VM:8003)
    ↓ heartbeat every 30s
MAS Device Registry (192.168.0.188:8001/api/devices/heartbeat)
    ↓
MAS /api/devices/network
    ↑
Website Device Manager, MYCA (when querying devices)
```

## MycoBrain Service

| Property | Value |
|----------|-------|
| Script | `services/mycobrain/mycobrain_service_standalone.py` |
| Port | 8003 |
| Health | `GET http://localhost:8003/health` |
| Devices | `GET http://localhost:8003/devices` |

## Heartbeat Payload

The service sends to `POST {MAS_REGISTRY_URL}/api/devices/heartbeat`:

- `device_name`, `device_role`, `device_id`
- `status`, `location`, `display_name`
- `last_seen`, `capabilities`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAS_REGISTRY_URL` | `http://192.168.0.188:8001` | MAS API for heartbeats |
| `MYCOBRAIN_DEVICE_NAME` | Local MycoBrain | Device name in registry |
| `MYCOBRAIN_DEVICE_ROLE` | standalone | mushroom1, sporebase, gateway, etc. |
| `MYCOBRAIN_HEARTBEAT_INTERVAL` | 30 | Seconds between heartbeats |

## How MYCA Can Query Devices

MYCA (and any client) can ask "what devices are online?" via:

```
GET {MAS_API_URL}/api/devices/network
```

Returns devices from the registry, including MycoBrain boards that have sent recent heartbeats.

## FCI Telemetry (Separate Path)

FCI (Fungal Computer Interface) telemetry flows to **Mycorrhizae** (`device.{id}.telemetry` channels), not directly to MAS. MYCA does not yet consume FCI telemetry for "lab state" awareness. See audit for Mycorrhizae→MYCA bridge recommendation.

## Related

- `services/mycobrain/mycobrain_service_standalone.py`  
- `.cursor/rules/mycobrain-always-on.mdc`  
- MAS `/api/devices/` routers  
