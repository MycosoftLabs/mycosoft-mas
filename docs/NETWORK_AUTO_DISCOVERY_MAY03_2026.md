# Network auto-discovery — LAN inventory (May 03, 2026)

**Date:** May 3, 2026  
**Status:** Complete  

## Purpose

Reconcile **UniFi**, **ARP/ping**, **MQTT** heartbeats, **HTTP service fingerprints**, and optional **Jetson SSH onboarder** into MINDEX Postgres table **`soc_ops.device_inventory`** (via MAS `soc` repository).

## Key code

| Component | Path |
|-----------|------|
| Discovery / reconciler | `mycosoft_mas/services/network_discovery.py` (and related helpers per rollout) |
| MAS inventory API | `GET /api/devices/inventory` (and diff/onboard routes if mounted) |
| Website | `WEBSITE/website/app/security/network/page.tsx` — tabs, live WS via security stream |

## Environment

- **MAS VM (188)** should reach UniFi controller and LAN `192.168.0.0/24`.  
- **Jetsons** e.g. `192.168.0.123`, `192.168.0.228` — probe `:8787`; onboarder uses `JETSON_*` / `VM_PASSWORD` from env (never committed).

## Verify

- MAS: inventory endpoint returns rows with `source`, `last_seen`, `classified_as`.  
- Website `/security/network`: counts match; unknown devices flagged for triage.
