# COM7 Board on Desk — Sandbox + Local Dev Cohesion

**Date:** February 18, 2026

## Goal

The MycoBrain board plugged into your desk on **COM7** should:

- Work on the **local dev machine** (localhost:3010 → discover sees COM7, network sees MAS devices).
- Appear and be controllable on the **sandbox** (sandbox.mycosoft.com → Device Network shows the board via MAS registry; commands from sandbox go through MAS to your PC).

## Architecture (short)

| Where        | What |
|-------------|------|
| **Dev PC**  | Board on COM7 → MycoBrain service (port 8003) → heartbeat to MAS (188) with **reachable host** (LAN IP or Tailscale). |
| **MAS (188)** | Device registry: `POST /api/devices/register` (heartbeat), `GET /api/devices` (list), `POST /api/devices/{id}/command` (proxy to device host:8003). |
| **Sandbox (187)** | Website container uses `MAS_API_URL=http://192.168.0.188:8001`. Device Network merges **discover** (sandbox MycoBrain 187:8003) + **network** (MAS registry). Your board appears from **network** because it’s registered by your PC’s heartbeat. |
| **Local dev** | Website uses `MYCOBRAIN_SERVICE_URL=http://localhost:8003` (discover) and `MAS_API_URL=http://192.168.0.188:8001` (network). Same board appears in discover (COM7) and in network (after heartbeat). |

## Prerequisites

1. **MAS** running on 192.168.0.188:8001 (device registry available).
2. **Dev PC** can reach MAS (e.g. `curl http://192.168.0.188:8001/health`).
3. **MAS (188)** can reach **dev PC** on port **8003** (for command proxy). Same LAN (192.168.0.x) is enough if Windows Firewall allows inbound TCP 8003 from 192.168.0.188 (or from 192.168.0.0/24).

## Steps

### 1. On the dev machine (board on COM7)

- Start **MycoBrain service** (so it binds to 0.0.0.0:8003 and can be reached by MAS):

  From MAS repo:

  ```bash
  cd path/to/mycosoft-mas
  set MAS_REGISTRY_URL=http://192.168.0.188:8001
  set MYCOBRAIN_HEARTBEAT_ENABLED=true
  python services/mycobrain/mycobrain_service_standalone.py
  ```

  Or use your existing start script (e.g. `scripts/start_mycobrain_service.ps1`) and ensure:

  - `MAS_REGISTRY_URL=http://192.168.0.188:8001`
  - `MYCOBRAIN_HEARTBEAT_ENABLED=true` (default is true).

- Ensure the board is on **COM7** (or whatever port the service auto-detects). The service’s port watcher will connect to it; heartbeat will then register it with MAS using the dev PC’s **reachable address** (LAN IP, or Tailscale if configured).

### 2. Firewall (so sandbox → MAS → dev PC works)

- On the **dev PC**, allow inbound **TCP 8003** from the MAS server (or whole LAN):

  - Windows: Windows Defender Firewall → Advanced → Inbound Rules → New Rule → Port 8003 TCP → Allow for 192.168.0.188 or 192.168.0.0/24.

- If you use **Tailscale**, the service can report a Tailscale IP and MAS will proxy to that; then only Tailscale connectivity is needed (no LAN firewall change required for LAN IP).

### 3. Run the cohesion test script

From the **MAS repo** on the dev machine:

```bash
# Default: uses localhost:3010 for website APIs
python scripts/test_mycobrain_com7_cohesion.py

# Test against sandbox (optional)
python scripts/test_mycobrain_com7_cohesion.py --website-url https://sandbox.mycosoft.com
```

The script checks:

- MAS health and `/api/devices` (list).
- Local MycoBrain health, `/ports` (COM7), `/devices` (connected).
- Waits for one heartbeat interval (~35 s), then re-checks MAS.
- Website `/api/devices/discover` and `/api/devices/network`.

If all pass, the board is registered with MAS and the website (local and/or sandbox) can show it and send commands via MAS.

### 4. Verify in the UI

- **Local:** Open http://localhost:3010 → NatureOS → Device Network. You should see the COM7 device from discover and the same device (or gateway) from the MAS network list.
- **Sandbox:** Open https://sandbox.mycosoft.com → NatureOS → Device Network. The board on your desk should appear in the **network** list (from MAS). Sending a command from the sandbox goes: Sandbox → MAS (188) → dev PC:8003 → board.

## Env reference

| Env (dev PC MycoBrain) | Purpose |
|------------------------|--------|
| `MAS_REGISTRY_URL`     | MAS base URL for heartbeat (default `http://192.168.0.188:8001`). |
| `MYCOBRAIN_HEARTBEAT_ENABLED` | Enable heartbeat (default `true`). |
| `MYCOBRAIN_PUBLIC_HOST` | Optional; force reachable host (e.g. Tailscale IP or Cloudflare host). |
| `MYCOBRAIN_SERVICE_PORT` | Port the service listens on (default 8003). |

| Env (website) | Local dev | Sandbox container |
|---------------|-----------|--------------------|
| `MAS_API_URL` | `http://192.168.0.188:8001` | `http://192.168.0.188:8001` |
| `MYCOBRAIN_SERVICE_URL` | `http://localhost:8003` | `http://192.168.0.187:8003` (sandbox host MycoBrain) |

## Troubleshooting

| Symptom | Check |
|--------|--------|
| Board not on sandbox | MAS reachable from dev PC? Heartbeat logs “Device … registered with MAS”? MAS `/api/devices` shows the device? Sandbox website uses `MAS_API_URL=188:8001`? |
| Commands from sandbox fail | Can MAS (188) reach dev PC:8003? (e.g. from 188: `curl http://DEV_PC_IP:8003/health`.) Windows Firewall allows 8003 from 188? |
| COM7 not in discover (local) | MycoBrain service running on dev PC? `MYCOBRAIN_SERVICE_URL=http://localhost:8003` in website `.env.local`? |
| No devices in network (local) | `MAS_API_URL` set to 188:8001? MAS up and registry returning 200 for `/api/devices`? |

## Related docs

- `docs/DEVICE_MANAGER_AND_GATEWAY_ARCHITECTURE_FEB10_2026.md` — Device manager and gateway architecture.
- `docs/SANDBOX_MYCOBRAIN_COM7_FEB18_2026.md` — Sandbox + COM7 visibility (board on desk via heartbeat).
- `docs/TAILSCALE_REMOTE_DEVICE_GUIDE_FEB09_2026.md` — Remote device access via Tailscale.
- Test script: `scripts/test_mycobrain_com7_cohesion.py`.
