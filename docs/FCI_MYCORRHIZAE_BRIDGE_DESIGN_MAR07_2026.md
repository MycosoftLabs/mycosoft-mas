# FCI / Mycorrhizae Bridge to MAS and MINDEX

**Date:** March 7, 2026  
**Status:** Design  
**Related:** MycoBrain Rail Unification, device registry, FCI driver, Mycorrhizae protocol

## Overview

Bridge Mycorrhizae/FCI summaries into MAS and MINDEX under a **single device_id**, so that one device (e.g. Mushroom 1 with FCI soil probe) has:

- MycoBrain BME688 telemetry (via heartbeat + ingest)
- FCI bioelectric summaries (via Mycorrhizae → bridge)

## Architecture

```
FCI/Mycorrhizae          Bridge                    MAS / MINDEX
      │                     │                           │
      │  device.{id}.fci    │  heartbeat extra          │
      ├────────────────────►│  or telemetry ingest      │
      │  or stream events   │  device_id aligned        │
      │                     ├──────────────────────────►│
      │                     │  POST /ingest             │
      │                     │  or envelope API          │
```

## Device ID Alignment

- **MycoBrain heartbeat** uses `device_id` = MAC-derived or configured (e.g. `a1b2c3d4`).
- **FCI/Mycorrhizae** must use the **same device_id** when the FCI probe is attached to that MycoBrain.
- Mycorrhizae channel: `device.{device_id}.fci` or `device.{device_id}.telemetry` with `source: "fci"`.

## Implementation Path

### 1. Mycorrhizae MINDEX client (existing)

`mycorrhizae-protocol/mycorrhizae/integrations/mindex_client.py` already extracts `device_id` from message header and persists to MINDEX. Ensure FCI messages include:

```json
{"hdr": {"deviceId": "<same-as-mycobrain>", "msgId": "..."}, "pack": [...], "ts": {...}}
```

### 2. MAS device extra (implemented)

`POST /api/devices/{device_id}/fci-summary` stores FCI summary in device `extra`:

- **Payload:** `{ "summary": {...}, "timestamp": "ISO8601", "source": "fci" }`
- **Stored:** `_device_registry[device_id]["extra"]["fci_summary"]`
- **Behavior:** Creates placeholder device if not yet registered (enables FCI-first flow)

### 3. Website ingest API (existing)

`POST /api/devices/ingest` accepts `deviceId` and `sensors`. FCI summaries can be sent as:

```json
{
  "deviceId": "<mycobrain-device-id>",
  "deviceType": "mycobrain",
  "sensors": { "fci_summary": {...} },
  "timestamp": "..."
}
```

## Next Steps

1. Add `POST /api/devices/{device_id}/fci-summary` to MAS device registry (stub).
2. Document device_id mapping in Mycorrhizae gateway config.
3. Extend Mycorrhizae pipeline to include device_id from MycoBrain registration.
