# Mycorrhizae→MYCA Telemetry Bridge — March 7, 2026

**Status:** Design / Future  
**Purpose:** Subscribe to Mycorrhizae `device.*.telemetry` and inject relevant lab state into MYCA context.  
**Related:** `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md`

---

## Overview

FCI telemetry flows to Mycorrhizae (`device.{id}.telemetry`). MYCA does not yet consume it. A bridge would:

1. Subscribe to Mycorrhizae channels (e.g. aggregate or device-specific)
2. Maintain a rolling window of recent telemetry
3. When MYCA handles a message, inject "Lab state: device X last reading at T" if relevant

## Mycorrhizae Channels

| Channel | Purpose |
|---------|---------|
| `device.{id}.telemetry` | Per-device FCI telemetry |
| `device.{id}.commands` | Commands to device |

## Bridge Design

- **Location:** New module in MAS, e.g. `mycosoft_mas/myca/bridges/mycorrhizae_telemetry_bridge.py`
- **Subscribe:** Mycorrhizae protocol subscribe API (HTTP SSE or WebSocket)
- **Cache:** In-memory deque of last N telemetry events per device (e.g. 10)
- **Injection:** When MYCA context is built, append `recent_telemetry_summary` if user asks about devices/lab

## Dependencies

- Mycorrhizae subscribe/stream API
- MAS context injection point in orchestrator
- Device registry for mapping IDs to names

## Not Yet Implemented

This is a medium-term upgrade. Document when built.

## Related

- `docs/MYCOBRAIN_TO_MAS_FLOW_MAR07_2026.md`
- Mycorrhizae protocol docs
- FCI telemetry struct in mycobrain firmware
