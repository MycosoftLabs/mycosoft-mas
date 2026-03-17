# MycoBrain Live-Network Control and COM5 Phantom Fix — Mar 7, 2026

**Date:** March 7, 2026  
**Status:** Implemented  
**Scope:** Fix phantom COM5, ensure board uses COM7, and document why live mycosoft.com cannot control a board on the user's PC.

---

## Problem Summary

1. **Phantom COM5** – Service reported COM5 as a device; COM5 is a virtual ACPI port, not the real MycoBrain board.
2. **Real board on COM7** – The only real board is on COM7.
3. **Live controls broken** – LED and control commands from mycosoft.com did not reach the board.
4. **Peripherals not scanning** – Peripheral scan failed because the wrong port was used.

---

## Root Cause: COM5 Hardcoding

COM5 was hardcoded or preferred in several places. COM5 is typically a virtual ACPI serial port on Windows, not a real USB serial device. Using it caused connection failures and broken controls.

---

## Fixes Applied

### 1) API route `/api/mycobrain` (Website)

- **POST default port:** Changed from `COM5` to `COM7`.
- **GET availablePorts filter:** Only returns ports with `likely_mycobrain === true`; COM5 is excluded via `is_likely_mycobrain_port()` (filters out ACPI virtual ports).

### 2) Network page `handleScan` (Website)

- Uses COM7 as primary fallback.
- Reads `availablePorts` from `GET /api/mycobrain` and prefers COM7, then first available port.
- Uses `p.port || p.device` for port names (service returns `device`).

### 3) MycoBrain service port restriction

- **`services/mycobrain/.env.local`** (gitignored): `MYCOBRAIN_ALLOWED_PORTS=COM7`
- Service uses `MYCOBRAIN_ALLOWED_PORTS` to restrict auto-discovery and connect to COM7 only.
- **Restart required:** Run `.\scripts\mycobrain-service.ps1 restart` so the service picks up `.env.local`.

### 4) Service `is_likely_mycobrain_port()`

- Filters out ACPI virtual ports (COM1, COM2, phantom COM5) by checking VID and `hwid`.
- Only real USB serial devices (Espressif, CH340, CP210x, etc.) are considered likely MycoBrain.

---

## Why Live mycosoft.com Cannot Control the Board

**Architecture constraint:** The board is physically connected to **your PC** via USB (COM7). The **live website** runs on **Sandbox VM 187**.

| Component        | Location        | What it sees                          |
|-----------------|-----------------|---------------------------------------|
| mycosoft.com    | VM 187          | Calls `localhost:8003` on **VM 187**  |
| MycoBrain service | Your PC (8003) | Board on COM7 on **your PC**          |

When you use **live mycosoft.com**, the website runs on VM 187. It calls `localhost:8003` on **VM 187**, not on your PC. There is no MycoBrain service or COM7 on VM 187, so controls cannot reach your board.

**Local dev works** because both the website (3010) and MycoBrain service (8003) run on your PC; `localhost:8003` points to the service that has COM7.

### How to Enable Live Control

To control the board from live mycosoft.com, one of these must be true:

1. **MycoBrain service + board on a LAN host reachable by VM 187**  
   - Run MycoBrain service on a machine that has the board (e.g. a Raspberry Pi or Jetson with the board plugged in).  
   - VM 187 must call `http://<that-host-IP>:8003` instead of `localhost:8003`.

2. **Tunnel or proxy**  
   - Expose your PC's MycoBrain service (8003) to the VM (e.g. via Tailscale, ngrok, or a reverse proxy).  
   - Configure the website to use that URL for MycoBrain.

3. **Gateway on VM 187**  
   - Plug the board into a machine that can reach VM 187 (e.g. a gateway on the same LAN) and run the MycoBrain service there.  
   - The website on 187 would call that gateway's MycoBrain API.

---

## Operational Steps

### Restart MycoBrain service (required after .env.local change)

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\mycobrain-service.ps1 restart
```

The script loads `services/mycobrain/.env.local` before starting, so `MYCOBRAIN_ALLOWED_PORTS=COM7` will be applied.

### Verify COM7 is used

```powershell
# Health check
Invoke-RestMethod http://localhost:8003/health

# Devices (should show COM7 only)
Invoke-RestMethod http://localhost:8003/devices
```

### Optional: Pin port at start

```powershell
.\scripts\mycobrain-service.ps1 start -AllowedPorts "COM7"
```

---

## Related Docs

- `docs/MYCOBRAIN_GATEWAY_NODE_RECOGNITION_MAR13_2026.md` – Gateway mode, MYCOBRAIN_ALLOWED_PORTS, MAS registration.
- `.cursor/rules/mycobrain-always-on.mdc` – MycoBrain service management.
