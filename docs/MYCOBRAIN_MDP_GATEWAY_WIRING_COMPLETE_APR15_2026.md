# MycoBrain MDP Gateway Command Wiring — Complete APR15 2026

**Date:** 2026-04-15  
**Status:** Complete  
**Commit:** `aaa13b2d8` (main)

## Delivered

1. **MAS** (`device_registry_api.py`): Resolves `mycobrain-service-*` / `board_type=service` registry rows to real MDP HTTP paths (`mycobrain-COM7`, etc.) via `extra.mdp_device_ids_on_host`, `extra.mdp_device_id`, or `GET {gateway}/devices`. Forwards optional `X-API-Key` using `MYCOBRAIN_SERVICE_FORWARD_API_KEY` or `MYCOBRAIN_API_KEY` on the orchestrator. Command and telemetry responses include `mdp_path_id` when applicable.
2. **Local MycoBrain service** (`mycobrain_service_standalone.py`): Heartbeat `extra` includes `mdp_device_ids_on_host` for connected serial devices; service-only heartbeat includes empty list placeholder.
3. **Docs:** `docs/API_CATALOG_FEB04_2026.md` (device command rows), `docs/MQTT_MAS_MINDEX_BRIDGE_APR13_2026.md` (MAS command subsection).

## Deploy

- **MAS VM 188:** `python scripts/_pull_and_restart_mas_vm188.py` (pull `main`, `systemctl restart mas-orchestrator`). Verified health includes `git_sha` matching commit.
- **Dev PC:** `.\scripts\mycobrain-service.ps1 start` after pull so the service runs the new heartbeat fields.

## Verify

- `GET http://192.168.0.188:8001/health` — orchestrator up.
- `POST http://192.168.0.188:8001/api/devices/{gateway_id}/command?use_mycorrhizae=false` with body `{"command":"status","params":{},"timeout":8}` — if no ESP on that gateway, **503** with explicit “no serial MDP device” message (proves resolver ran).
- With ESP connected and auto-connected: same POST should return **200** and `mdp_path_id` in the nested response.

## Website / local dev wiring (no code change required)

- `.env.local`: `MAS_API_URL=http://192.168.0.188:8001`, `NEXT_PUBLIC_MAS_API_URL` same, `MYCOBRAIN_SERVICE_URL=http://localhost:8003` (or your LAN IP if the browser must hit the service from another host).
- Jetson / secured gateway: set **`MYCOBRAIN_SERVICE_FORWARD_API_KEY`** on **MAS** (188) to match the MycoBrain service `MYCOBRAIN_API_KEY`, then restart `mas-orchestrator`.

## Follow-up (optional)

- Set `extra.mdp_device_id` from firmware on multi-board gateways to avoid ambiguity.
- Purge stale `mycobrain-service-*` rows if duplicate entries confuse the UI (TTL expires after heartbeat stops).
