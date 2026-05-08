# Meshtastic TennMesh integration — operator closeout (May 06, 2026)

**Purpose:** Close remaining execution items from the TennMesh plan: broker ACL posture, smoke tests, data-path verification (no fabricated hardware rows), optional gateway registry sidecar, and local website proxy checks.

**Plans (read-only reference):** `meshtastic_tennmesh_map_integration_58c0b3f3.plan.md`, `meshtastic_lan_mqtt_integration_78ae6738.plan.md`.

---

## 1. Verified from automation host (May 06, 2026)

| Check | Result |
|--------|--------|
| `GET http://192.168.0.188:8001/api/meshtastic/stats` | **200** — `node_count` 0, packet counters 0 (quiet mesh / no uplink during probe). |
| `GET http://192.168.0.188:8001/api/meshtastic/packets?limit=5` | **200** — `items: []` until live RF + MQTT uplink fills MINDEX. |
| `GET http://192.168.0.189:8000/health` | **200** — `{"status":"healthy"}`. |
| TCP `192.168.0.189:6379` | Reachable from LAN; `XRANGE mesh:packets` returned **no entries** when mesh quiet (stream exists). |
| SSH `mycosoft@192.168.0.196` | **OK** — hostname `mycobrain-mqtt` context; see broker section below. |

---

## 2. Broker VM 196 — Mosquitto + ACL posture

- **Runtime:** Docker container **`mycobrain-mqtt`** maps **1883** (MQTT) and **9001** (WebSockets).
- **Host config dir:** `/opt/mycobrain/mqtt-broker/config/`
  - `mosquitto.conf`: listeners **0.0.0.0:1883** and **9001**, **`allow_anonymous false`**, **`password_file /mosquitto/config/passwd`**.
  - **No `acl_file`** is present in that directory — authorization is **username/password only** (authenticated clients are not restricted to `msh/#` vs MDP topics by broker ACL lines). If topic isolation is required (Meshtastic subscribe-only user, MDP publishers unchanged), add an **`acl_file`** in Mosquitto and mount it beside `mosquitto.conf`, then restart the container.
- **`systemctl is-active mosquitto`:** **inactive** on host — expected when Mosquitto runs **inside Docker**, not as host `mosquitto.service`.
- **Bridge:** `mqtt-meshtastic-bridge.service` **active** on **196** (subscribe **`msh/#`** → MINDEX + Redis).

### Broker smoke (no secrets in this doc)

**Automated (loads `WEBSITE/website/.credentials.local` — password never printed):**

| Script | Purpose |
|--------|---------|
| `scripts/mqtt_broker_auth_smoke_ssh.py` | Confirms **`mycobrain` + `MQTT_BROKER_PASSWORD`** against **`$SYS/broker/version`** inside **`mycobrain-mqtt`**. |
| `scripts/mqtt_mesh_smoke_ssh.py` | **`msh/#`** sample (**`-W 70`**); exit **27** / empty stdout = **timeout with no mesh MQTT traffic** (normal if radios are quiet or uplink off). |
| `scripts/mqtt_isolated_topic_ping_ssh.py` | Retained publish + subscribe under **`mycosoft/internal/mqtt-smoke/<uuid>`** — proves LAN pub/sub auth without touching **`msh/#`**. |

**Manual**

1. **Anonymous denied:** `sudo docker exec mycobrain-mqtt mosquitto_sub -h 127.0.0.1 -p 1883 -t '$SYS/broker/version' -C 1 -W 4 -u invalid -P invalid` → expect **not authorised** (broker listening).
2. **Mesh traffic:** With broker credentials:  
   `sudo docker exec mycobrain-mqtt mosquitto_sub -h 127.0.0.1 -p 1883 -u '<user>' -P '<secret>' -t 'msh/#' -v` — leave **30–120 s**; output appears when radios uplink. Quiet mesh → empty output is normal.

### Optional non-mesh publish test

Prefer **`scripts/mqtt_isolated_topic_ping_ssh.py`** (random topic under `mycosoft/internal/mqtt-smoke/`). Avoid flooding **`msh/#`**.

---

## 3. MINDEX packets + Redis (quiet vs live)

- **Packets:** Use **`GET http://192.168.0.188:8001/api/meshtastic/packets?limit=50`** (MAS proxies MINDEX). Empty **`items`** is valid until ingest occurs.
- **Redis stream:** From any host with LAN access to **189:6379** and `redis-cli` or Python **redis**:  
  `XRANGE mesh:packets - + COUNT 10` — confirms stream **existence**; entry count follows bridge activity.

---

## 4. Hardware inventory (operator — real data only)

Record **actual** COM ports, roles, and firmware strings when devices are connected (no placeholder COMs in production docs).

| Board ID | LilyGO variant | Site / role | Windows COM | Firmware (verified) | MQTT uplink tested |
|----------|----------------|---------------|-------------|------------------------|--------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |

**Firmware pin (example):** **v2.7.15.567b8ea** — confirm current assets at [Meshtastic firmware releases](https://github.com/meshtastic/firmware/releases) before flashing.

Per-board steps: flash → `meshtastic --port COMx --info` → align **region**, **modem preset**, **channel name + PSK**, **MQTT** to **192.168.0.196:1883** with broker credentials, **uplink ON**, sensible **position** interval for map overlays.

---

## 5. Website localhost proxy (operator)

1. In **`WEBSITE/website/.env.local`**, set **`MAS_API_URL=http://192.168.0.188:8001`** (or your LAN MAS URL).
2. `npm run dev` (port **3010** per project convention).
3. Open **`/natureos/meshtastic/map`** and **`GET http://localhost:3010/api/meshtastic/packets?limit=50`** — should proxy via Next.js to MAS; overlays populate when MINDEX has position-bearing payloads.

---

## 6. Optional registry sidecar (gateway metadata)

Script: **`scripts/meshtastic_gateway_registry_ping.py`** — POSTs **`/api/devices/heartbeat`** with **`registry_kind: meshtastic_mqtt_gateway`** and optional **`MESHTASTIC_NODE_ID`** / **`MESHTASTIC_SITE_LABEL`**.

Example (secrets via env only):

```bash
export MAS_URL=http://192.168.0.188:8001
export MESHTASTIC_GATEWAY_REGISTRY_ID=meshtastic-bridge-vm196
export MESHTASTIC_NODE_ID='!xxxxxxxx'
export MESHTASTIC_SITE_LABEL=north-tower
python scripts/meshtastic_gateway_registry_ping.py
```

Schedule with **cron** or **systemd timer** on **196** alongside the bridge if you want MYCA device lists to include the gateway row.

---

## 7. Unified network index (MAS)

For a single merged view of MycoBrain heartbeats + Meshtastic nodes + observers, use **`GET /api/devices/unified-network`** on MAS (see **`docs/API_CATALOG_FEB04_2026.md`**).

---

## 8. Related docs

- `docs/MESHTASTIC_TENNMESH_INTEGRATION_COMPLETE_MAY05_2026.md`
- `docs/MESHTASTIC_MAS_MINDEX_CHAIN_VERIFY_MAY05_2026.md`
- `docs/MESHTASTIC_MQTT_ENABLE_DEVICE_CRASH_WORKAROUNDS_MAY05_2026.md`
