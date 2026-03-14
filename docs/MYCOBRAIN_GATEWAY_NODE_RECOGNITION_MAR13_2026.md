# MycoBrain Gateway Node Recognition — Mar 13, 2026

**Date:** March 13, 2026  
**Status:** Implemented and verified  
**Scope:** Ensure a MycoBrain board plugged by serial into a LAN machine is immediately recognized as a **gateway node** in MAS and visible to sandbox device network flows.

---

## Objective

Make the "board on local COM7" flow production-aligned with gateway architecture:

1. Local serial board is ingested by local MycoBrain service.
2. Heartbeat registers into MAS Device Registry as `device_role=gateway`.
3. Sandbox/website sees it through MAS network device APIs.
4. MAS command proxy can call the gateway node over LAN.

---

## Code Changes

### 1) Serial port pinning for deterministic gateway ingestion

Updated `services/mycobrain/mycobrain_service_standalone.py`:

- Added environment support:
  - `MYCOBRAIN_ALLOWED_PORTS` (comma-separated, example: `COM7` or `/dev/ttyUSB0,/dev/ttyACM0`)
- Port watcher and connect path now enforce allowed ports:
  - Auto-discovery only returns ports in `MYCOBRAIN_ALLOWED_PORTS` (when set).
  - `/devices/connect/{port}` rejects ports outside the allowlist.

This prevents accidental device drift and ensures gateway identity is tied to the intended serial port.

### 2) Gateway-mode startup in service manager

Updated `scripts/mycobrain-service.ps1`:

- Added optional parameters:
  - `-Mode gateway|standalone`
  - `-AllowedPorts "COM7"` (or Linux serial list)
- Added optional `.env` loader from:
  - `services/mycobrain/.env.local`
- Start now logs effective role and allowed ports.

### 3) One-command local gateway bring-up

Added `scripts/start-mycobrain-gateway-local.ps1`:

- Sets gateway runtime env contract:
  - `MYCOBRAIN_DEVICE_ROLE=gateway`
  - `MYCOBRAIN_DEVICE_NAME=MycoBrain Gateway Node`
  - `MYCOBRAIN_DEVICE_LOCATION=Yard Gateway`
  - `MYCOBRAIN_ALLOWED_PORTS=COM7` (default; configurable)
  - `MAS_REGISTRY_URL=http://192.168.0.188:8001`
- Restarts MycoBrain service through service manager.
- Verifies local health and MAS gateway entries.

---

## Validation Performed

Validated from this machine and MAS:

1. Local service healthy on `http://localhost:8003/health`.
2. Local serial device connected on `COM7` via `GET /devices`.
3. MAS registry entry confirmed:
   - `device_id: mycobrain-COM7`
   - `device_role: gateway`
   - `capabilities: service, serial, lora, bluetooth, wifi, sim, store_and_forward`
4. MAS command proxy confirmed end-to-end:
   - `POST /api/devices/mycobrain-COM7/command`
   - Successful `status` command response returned through MAS.

---

## Operational Usage

Run local gateway mode:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/start-mycobrain-gateway-local.ps1" -AllowedPorts "COM7"
```

Quick checks:

```powershell
curl.exe -sS "http://localhost:8003/health"
curl.exe -sS "http://localhost:8003/devices"
curl.exe -sS "http://192.168.0.188:8001/api/devices?include_offline=true"
```

---

## Notes

- This flow is the direct precursor for the combined **Jetson + MycoBrain gateway node** model.
- Current validation confirms serial gateway identity + MAS visibility + MAS command routing over LAN.
- Next expansion is transport ingestion fan-in on gateway (`lora`, `wifi`, `bluetooth`, `sim`) into this same gateway identity path.
