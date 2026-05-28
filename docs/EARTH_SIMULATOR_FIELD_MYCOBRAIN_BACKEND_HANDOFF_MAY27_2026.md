# Earth Simulator Field MycoBrain Backend Handoff

**Date:** May 27, 2026  
**Status:** Backend + website UI merged to `main` — **Codex deploy only** (blue/green)  
**Devices:** Mushroom 1 (192.168.0.123:8787), Hyphae 1 (192.168.0.228:8787)

**Codex deploy handoff:** `WEBSITE/website/docs/codex-handoffs/FIELD_MYCOBRAIN_DEPLOY_HANDOFF_MAY27_2026.md`  
**Website `main`:** `0b752fc7` | **MAS `main`:** `259032777` (orchestrator restarted on 188)

---

## What was done (backend only)

### 1. Field deployment registry (fixed map coordinates + agent URLs)

| Registry ID | Role | Host | Agent URL | Map location |
|-------------|------|------|-----------|--------------|
| `mycobrain-mushroom1-jetson-123` | mushroom1 | 192.168.0.123 | http://192.168.0.123:8787 | 32.715736, -117.161087 (San Diego) |
| `mycobrain-hyphae1-jetson-228` | hyphae1 | 192.168.0.228 | http://192.168.0.228:8787 | 32.640278, -117.085833 (Southwestern College, Chula Vista) |

**Files:**
- `WEBSITE/website/lib/devices/field-deployments.ts` — source of truth for Codex
- `WEBSITE/website/lib/devices/operator-probe.ts` — LAN probe helper (`/api/status`, `/api/sensor`)
- `WEBSITE/website/lib/devices/catalog.ts` — `default_location` set for `mushroom-1` and `hyphae-1`

### 2. Earth Simulator devices API (replaces Local MycoBrain-only path)

**`GET /api/earth-simulator/devices`** now merges:

1. Device catalog (types)
2. Field deployments (fixed SD / Chula Vista coords)
3. **MAS registry** (`MAS_API_URL/api/devices`) — works on prod without LAN
4. LAN operator probes when the website server can reach 192.168.0.x
5. Local `:8003` serial service (dev only)

**Response shape (per device for map markers):**

```json
{
  "id": "mushroom-1",
  "registry_id": "mycobrain-mushroom1-jetson-123",
  "name": "Mushroom 1",
  "role": "mushroom1",
  "status": "connected",
  "location": { "lat": 32.715736, "lon": -117.161087 },
  "telemetry": { "temperature_c": 33.5, "humidity_pct": 25.1, "iaq": 143, ... },
  "agent_url": "http://192.168.0.123:8787",
  "host": "192.168.0.123",
  "source": "operator"
}
```

**Status mapping for markers:** `online` / `connected` → green (`status === "connected"` in `device-markers.tsx`).

### 3. Device Network API

**`GET /api/devices/network`** now adds:

- `agent_url`, `location_coords`, `location_label`, `telemetry`
- Field deployment fallback when MAS is empty/unreachable
- Live LAN probe overlay (online status + telemetry when sandbox cannot reach LAN but MAS has cached heartbeats)

### 4. MAS device registry — agent :8787 routing

**`mycosoft_mas/core/routers/device_registry_api.py`:**

- Detects `api_kind: agent` / port `8787` / `extra.agent_url`
- Telemetry: `/telemetry/latest`, `/api/sensor`, `/api/status` (legacy operator paths)
- Commands: `/command`, `/api/command`, or legacy `/devices/{id}/command`

### 5. MQTT bridge — `mycosoft/devices/+/presence|telemetry`

**`mycosoft_mas/integrations/mqtt_mycobrain_bridge.py`:**

- Subscribes to legacy `mycobrain/#` **and** `mycosoft/devices/#`
- Maps `presence` → MAS heartbeat with field registry IDs keyed by `host_ip`
- Maps `telemetry` → MINDEX envelope + optional heartbeat

### 6. Field heartbeat bridge (always-on for prod)

**`scripts/field_mycobrain_heartbeat_bridge.py`**

- Probes both `:8787` agents every 30s
- Posts to `POST http://192.168.0.188:8001/api/devices/heartbeat`
- **Verified working** — both devices online in MAS with live BME688 telemetry

**Always-on placement (May 27, 2026): MAS VM 188 — not the MQTT broker, not dev PC**

| Service | Host | Why |
|---------|------|-----|
| `mycosoft-field-mycobrain-heartbeat` | **192.168.0.188** (systemd) | Always on; reaches 123/228 + MAS; feeds prod website via registry |
| `mycosoft-mqtt-mycobrain-bridge` | **192.168.0.188** (optional) | Subscribes to broker **196**; enable when `MQTT_PASSWORD` is in `.env.field-mycobrain` |

Install / status:

```bash
python scripts/install_field_mycobrain_services.py
python scripts/install_field_mycobrain_services.py --status
python scripts/install_field_mycobrain_services.py --enable-mqtt   # after MQTT_PASSWORD in .credentials.local
```

Do **not** run only on the MQTT broker VM — it cannot HTTP-probe Jetson operator UIs at `:8787`.

```powershell
cd MAS/mycosoft-mas
python scripts/field_mycobrain_heartbeat_bridge.py          # dev PC manual only
python scripts/field_mycobrain_heartbeat_bridge.py --once   # single cycle
```

---

## Verified locally (May 27, 2026)

```text
GET http://localhost:3010/api/earth-simulator/devices
→ 2 devices with coords + live telemetry (IAQ ~143 @ SD, ~61 @ Chula Vista)

GET http://192.168.0.188:8001/api/devices
→ mycobrain-mushroom1-jetson-123, mycobrain-hyphae1-jetson-228 both online

Both agents reachable:
→ http://192.168.0.123:8787/api/status
→ http://192.168.0.228:8787/api/status
```

---

## Website UI (merged to `main` May 27 — Codex deploy only)

Cursor merged device control fixes to **`main`** (`0f519c13`, `0b752fc7`). Codex should deploy via **Instant Deploy / ci-cd blue-green** — **not** `_rebuild_sandbox.py`.

Delivered in website:

1. Earth Simulator quick controls (beep / rainbow / off) via `POST /api/devices/network/{registryId}/command`
2. Device Manager → network registry first (`/natureos/devices/network`)
3. `lib/devices/operator-commands.ts` — correct Jetson operator strings
4. Device widget **Open Device Manager** link

**Deploy handoff:** `docs/codex-handoffs/FIELD_MYCOBRAIN_DEPLOY_HANDOFF_MAY27_2026.md`

### Optional UI fields from API

| Field | Use |
|-------|-----|
| `telemetry.temperature_c` | Live temp |
| `telemetry.humidity_pct` | Live RH |
| `telemetry.iaq` | Air quality |
| `telemetry.pressure_hpa` | Pressure |
| `agent_url` | Deep link / control panel base |
| `registry_id` | MAS command + telemetry paths |

---

## Deploy checklist (Codex)

### Website (187 / sandbox) — **blue/green only**

1. **`main` @ `0b752fc7` already on GitHub** — run Instant Deploy or ci-cd
2. Cutover via `scripts/blue-green-deploy.sh` (proxy + blue/green)
3. Cloudflare purge everything
4. **Do not** run `_rebuild_sandbox.py`
5. Ensure `MAS_API_URL=http://192.168.0.188:8001` in container env

### MAS (188) — **done**

1. `device_registry_api.py` deployed @ `259032777`
2. `mas-orchestrator` restarted
3. Start **field heartbeat bridge** on 188 (or keep on dev PC if always on LAN):
   ```bash
   python scripts/field_mycobrain_heartbeat_bridge.py
   ```
4. Optional: start MQTT bridge if agents publish to `192.168.0.196:1883`:
   ```bash
   MQTT_BROKER_HOST=192.168.0.196 MQTT_USERNAME=mycobrain MQTT_PASSWORD=$env:MYCOBRAIN_MQTT_PASSWORD python scripts/mqtt_mycobrain_bridge.py
   ```

### MQTT (when agents publish presence)

- LAN: `mqtt://192.168.0.196:1883` user `mycobrain`
- Remote: `wss://mqtt.mycosoft.com:443` (MQTT subprotocol, not raw WS)
- Topics: `mycosoft/devices/{mdp_id}/presence`, `.../telemetry`

---

## Files changed

| Repo | File |
|------|------|
| WEBSITE | `lib/devices/field-deployments.ts` (new) |
| WEBSITE | `lib/devices/operator-probe.ts` (new) |
| WEBSITE | `lib/devices/catalog.ts` |
| WEBSITE | `app/api/earth-simulator/devices/route.ts` |
| WEBSITE | `app/api/devices/network/route.ts` |
| MAS | `mycosoft_mas/integrations/mqtt_mycobrain_bridge.py` |
| MAS | `mycosoft_mas/core/routers/device_registry_api.py` |
| MAS | `scripts/field_mycobrain_heartbeat_bridge.py` (new) |

---

## Known limits

- **Sandbox VM (187) cannot HTTP-probe 123/228** — prod relies on MAS heartbeats (bridge) or MQTT.
- **Same MDP device_id** on both boards (`mycobrain-sidea-10b41d`) — always use **registry_id** for UI/MAS commands.
- **Local MycoBrain service** (`mycobrain-service-192-168-0-241`) still in MAS registry — Earth Simulator API filters to catalog/field ids; Codex should not bind widgets to gateway rows.
