# MQTT → MAS + MINDEX Bridge APR13 2026

**Date:** 2026-04-13  
**Status:** Implemented (bridge script + tests)  
**Related:** `docs/MQTT_LAN_WSS_DEPLOYMENT_AND_JETSON_HANDOFF_APR08_2026.md`

## Purpose

Subscribe to the LAN MQTT broker (default `192.168.0.196:1883`), receive Jetson / MycoBrain publishes, and forward:

1. **MAS Device Registry** — `POST {MAS_API_URL}/api/devices/heartbeat` so devices appear in `/api/devices/network`, `/api/mycobrain`, and CREP MycoBrain layer.
2. **MINDEX telemetry** — `POST {MINDEX_API_URL}/api/mindex/telemetry/envelope` with `X-Internal-Token` so samples land in `telemetry.*` tables.

## Topic contract (prefix default `mycobrain`)

| Topic | Body | Action |
|-------|------|--------|
| `{prefix}/{device_id}/heartbeat` | JSON (optional fields; see MAS `DeviceHeartbeat`) | Register/update device in MAS |
| `{prefix}/{device_id}/envelope` | Full MINDEX envelope (`hdr`, `pack`, `seq`, `ts`, …) | Ingest telemetry only |
| `{prefix}/{device_id}/telemetry` | Simplified: `pack` or `readings` array of `{id, v, u}` | Synthesize envelope + optional MAS heartbeat |

Set `MQTT_BRIDGE_HEARTBEAT_ON_TELEMETRY=0` to disable implicit heartbeat on `telemetry` messages.

### MAS `POST /api/devices/{id}/command` vs gateway-only heartbeats (Apr 15, 2026)

If the registry still has a **`mycobrain-service-*`** row (HTTP service waiting for USB), MAS **resolves** the real MDP id (`mycobrain-COM7`, etc.) via `GET http://{host}:{port}/devices` on that gateway or via heartbeat `extra.mdp_device_ids_on_host` / `extra.mdp_device_id`. Jetson gateways that require API keys: set **`MYCOBRAIN_SERVICE_FORWARD_API_KEY`** (or **`MYCOBRAIN_API_KEY`**) on the **MAS** orchestrator host so forwarded calls include `X-API-Key`.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER_HOST` | `192.168.0.196` | Broker |
| `MQTT_BROKER_PORT` | `1883` | Port |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | — | Auth (falls back to `MYCOBRAIN_MQTT_*`) |
| `MQTT_TOPIC_PREFIX` | `mycobrain` | First segment of topics |
| `MAS_API_URL` | `http://192.168.0.188:8001` | MAS orchestrator |
| `MINDEX_API_URL` | `http://192.168.0.189:8000` | MINDEX API |
| `MINDEX_INTERNAL_TOKEN` | — | Required for MINDEX ingest (or first entry in `MINDEX_INTERNAL_TOKENS`) |
| `MQTT_BRIDGE_DEFAULT_HOST` | `127.0.0.1` | Heartbeat `host` if omitted in JSON |
| `MQTT_BRIDGE_DEFAULT_PORT` | `8003` | Heartbeat port default |
| `MQTT_BRIDGE_DEFAULT_BOARD` | `jetson` | `board_type` default |
| `LOG_LEVEL` | `INFO` | Logging |

## Run

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
# Load .env / .credentials.local for MINDEX_INTERNAL_TOKEN, MQTT password
poetry install
poetry run python scripts/mqtt_mycobrain_bridge.py
```

Deploy as a **systemd service** on MAS VM (188) or any host that can reach broker + MAS + MINDEX on the LAN.

## Jetson publish examples

**Heartbeat (every 30s recommended):**

Topic: `mycobrain/jetson-gw-01/heartbeat`

```json
{
  "device_name": "Jetson Gateway",
  "host": "192.168.0.123",
  "port": 8003,
  "device_role": "gateway",
  "board_type": "jetson",
  "location": "37.0,-122.0",
  "capabilities": ["mqtt", "gateway"]
}
```

**Telemetry (samples):**

Topic: `mycobrain/jetson-gw-01/telemetry`

```json
{
  "pack": [
    {"id": "cpu_temp_c", "v": 41.2, "u": "C"},
    {"id": "link_rssi_dbm", "v": -62, "u": "dBm"}
  ]
}
```

## Verification

1. Bridge logs: `MAS heartbeat ok`, `MINDEX envelope ok`.
2. MAS: `GET {MAS}/api/devices?include_offline=true` — device listed.
3. Website: `/api/devices/network` and `/api/mycobrain` — same device metadata.
4. CREP: MycoBrain layer — device markers from merged MAS list.
5. MINDEX: `GET {MINDEX}/api/mindex/telemetry/devices/latest` (internal auth) — samples for device slug.

## Code

- `mycosoft_mas/integrations/mqtt_mycobrain_bridge.py`
- `scripts/mqtt_mycobrain_bridge.py`
- `tests/test_mqtt_mycobrain_bridge.py`
