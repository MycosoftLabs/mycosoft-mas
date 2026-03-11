# MycoBrain, Device Manager, CREP, and Fleet Survey Audit — March 7, 2026

**Status:** Survey Complete + Fixes In Progress  
**Date:** March 7, 2026  
**Context:** User reported device not showing on CREP, registry showing offline when device is plugged in, phantom 8003 device, device map empty, telemetry loading, alerts slow, fleet management unclear.

---

## Architecture Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| **MycoBrain Service** | localhost:8003 (or VM) | Serial comms, device connection, heartbeat to MAS |
| **MAS Device Registry** | 192.168.0.188:8001/api/devices | In-memory registry; devices register via POST /register |
| **Website /api/devices/network** | Proxies to MAS | Fetches devices for Device Manager, CREP, Map |
| **Website /api/mycobrain** | Proxies to localhost:8003 | Local service health, devices, connect/control |
| **Website /api/devices/discover** | Local discovery | Serial port scan |
| **Device Map** | /natureos/devices/map | MapLibre map; only shows devices with valid lat,lng in `location` |
| **CREP Dashboard** | /dashboard/crep | Uses same device sources for device widgets |

---

## Flow: How a Device Gets "Online"

1. **MycoBrain Service** (8003) connects to COM7 via port watcher (every 2s).
2. **Heartbeat loop** (every 30s) sends `POST {MAS_REGISTRY_URL}/api/devices/heartbeat` for each connected device.
3. **MAS** stores device in `_device_registry`, updates `_device_last_seen`.
4. **Status** = online if last_seen within 60s; stale 60–120s; offline >120s.
5. **Website** fetches via `/api/devices/network` → MAS `/api/devices` → returns devices with status.

---

## Root Cause Analysis

### 1. Registry Shows "MycoBrain Service Offline" When Device Is Plugged In

**Cause:** The network page checks `/api/mycobrain` for service status. That route:
- Fetches `localhost:8003/health` (3s timeout)
- If fetch fails or times out → returns `error: "MycoBrain service not running"`
- Service status UI uses `!data.error` — but when fallback returns network devices without `error`, it can show online incorrectly.

**Fix:** Use `serviceHealthy` when present; increase health check timeout; ensure consistent error handling.

### 2. CREP Device Widget Red / Cannot Interact

**Cause:** CREP uses the same MAS device registry. If devices show "offline" in registry (heartbeat not reaching MAS, or TTL expired), CREP shows red. Also: CREP device widget may use a different data path — needs verification.

### 3. Phantom "8003 Local Micro Brain" Device

**Cause:** When **no devices** are connected, the heartbeat loop sends a service-only payload with `device_id: mycobrain-service-{host}`. That appears in the registry. When COM7 later connects, both the real device (mycobrain-COM7) and the stale service entry can coexist until the service one expires (TTL 120s). If the service restarts often, the phantom keeps getting re-registered.

**Fix:** Do not register the service gateway when devices are connected. Consider expiring the service entry faster when real devices appear.

### 4. Device Map: "No Device Locations Available"

**Cause:** `LiveMapContent` only renders devices where `parseLocation(device.location)` returns valid [lng, lat]. MycoBrain devices have `location: "Unknown"` (default). So they never appear on the map.

**Fix:** 
- Always show the map (base layer).
- Improve empty state: "Devices need a location (lat,lng) in the registry. MycoBrain boards without GPS won't appear — add a fixed location in MAS for lab devices."
- Option: show a sidebar list of devices without locations when map has no points.

### 5. Telemetry Loading Forever

**Cause:** Telemetry is fetched from `{device_host}:{device_port}/devices/{device_id}/telemetry`. For local serial devices, `host` is the PC's LAN IP. The website runs server-side and proxies to MAS; MAS proxies to the device. If the device's host (user's PC) is not reachable from the server making the request (e.g., sandbox VM cannot reach dev PC), telemetry fails.

**Context:** When dev runs locally, website → MAS → device. MAS runs on VM 188. Device has host = user's PC IP. VM 188 must reach the user's PC. On same LAN, this usually works. Timeout or firewall can cause "loading forever."

### 6. Peripheral Scanning Turning On/Off

**Cause:** Port watcher runs every 2s. If the service process restarts (crash, killed, or multiple instances fighting for the port), scanning would stop and start. Also: `_get_mycobrain_port_names` filters to real USB ports; COM1 (virtual ACPI) is excluded. If COM7 disappears and reappears (driver, USB power, Windows), the watcher would disconnect and reconnect.

### 7. Slow Button Activation

**Cause:** Serial command has 2s timeout; firmware response may be slow. Port watcher reconnection could also introduce latency. Consider increasing timeout for control commands.

### 8. Alerts Slow to Load

**Cause:** Alerts page needs audit — likely separate API with its own latency.

### 9. COM7 Routing to Different Port

**Cause:** Windows can reassign COM ports when devices are unplugged/replugged or when enumeration order changes. The port watcher uses whatever ports `_get_mycobrain_port_names` returns. If COM7 becomes COM8, the device_id would change (mycobrain-COM8), and the old mycobrain-COM7 would expire.

---

## Data Sources by Page

| Page | Primary Source | Fallback |
|------|----------------|----------|
| Device Manager (Network) | /api/devices/discover + /api/devices/network | — |
| Device Map | /api/devices/network (include_offline=true) | — |
| CREP device widget | TBD (likely /api/devices/network or CREP unified) | — |
| Registry | MAS /api/devices | — |
| Service status | /api/mycobrain → localhost:8003/health | — |

---

## Fixes Applied (This Session)

1. **Service status:** Use `serviceHealthy` from `/api/mycobrain` when available; increased health timeout to 5s.
2. **Device map:** Improved empty state with `pointer-events-none` overlay; clearer copy for lab devices without GPS.
3. **CREP device widget:** Switched from `/api/mycobrain/devices` to `/api/mycobrain` so CREP gets merged local + MAS registry data and fallback when service is down.
4. **CREP Services Panel:** MycoBrain status now fetched from `/api/mycobrain`; shows real device count; polls every 15s.
5. **Timeouts:** Health check 5s; MycoBrain device fetch 8s in CREP.
6. **API responses:** Added `serviceHealthy: false` to all fallback paths in `/api/mycobrain` for consistent client logic.

---

## Recommended Next Steps

- [x] Audit CREP device widget data source — DONE: now uses /api/mycobrain.
- [ ] Audit alerts and fleet dashboards (insights, telemetry trends, fleet health).
- [ ] Add MYCOBRAIN_DEVICE_LOCATION for lab devices (e.g. "32.72,-117.16") so they appear on map.
- [ ] Consider a "device reachability" check: when displaying a device, verify we can reach host:port from the requesting context.
