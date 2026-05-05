# Meshtastic TennMesh-style integration — complete (May 03, 2026)

**Status:** Complete (code + operator runbooks). **VM execution** of Mosquitto audit, bridge install, and radio flash requires LAN access, `Mycosoft-mas/.credentials.local` (or `VM_PASSWORD` in process env) for SSH, and physical access to LilyGO boards.

**Related plan:** `.cursor/plans/meshtastic_tennmesh_map_integration_58c0b3f3.plan.md` (do not edit as part of this deliverable).

---

## 1. Delivered artifacts (repo)

| Item | Path |
|------|------|
| **Website — position decode** | `WEBSITE/website/lib/meshtastic/payload-position.ts` |
| **Website — packet → stream** | `WEBSITE/website/lib/meshtastic/packet-to-stream.ts` |
| **Website — SWR hook** | `WEBSITE/website/hooks/use-meshtastic-packets.ts` |
| **Website — map wrapper** | `WEBSITE/website/components/meshtastic/MeshtasticMeshMapWithActivity.tsx` |
| **Website — NatureOS map page** | `WEBSITE/website/app/natureos/meshtastic/map/page.tsx` (uses activity overlay) |
| **SSH smoke script** | `MAS/mycosoft-mas/scripts/meshtastic_plan_ssh_smoke.py` (TCP 22 + optional Paramiko `hostname`) |
| **systemd unit template** | `MAS/mycosoft-mas/scripts/vm/mqtt-meshtastic-bridge.service` |
| **Env template (placeholders only)** | `MAS/mycosoft-mas/scripts/vm/meshtastic-bridge.env.example` |
| **VM install helper** | `MAS/mycosoft-mas/scripts/vm/install_meshtastic_bridge_systemd.sh` |

**Bridge source (unchanged):** `mycosoft_mas/integrations/mqtt_meshtastic_bridge.py` — env vars: `MESHTASTIC_MQTT_HOST`, `MINDEX_API_URL`, `MINDEX_INTERNAL_TOKEN` / HMAC pair, `REDIS_URL`, `STREAM_KEY` = `mesh:packets`.

---

## 2. Verification run (this session)

| Check | Result |
|-------|--------|
| **TCP 22** to `192.168.0.196`, `.187`, `.188`, `.189` | All reachable from dev PC |
| **Paramiko SSH** with `hostname` | Skipped — `VM_PASSWORD` / `VM_SSH_PASSWORD` not present in process env (no `.credentials.local` loaded in that shell or file absent). **Action:** load credentials before `ssh_exec` MCP or Paramiko. |
| **MCP `ssh_exec`** | Error: credentials not found — same as above |
| **MAS `GET /api/meshtastic/*` on 188:8001** | **404** on `/stats` and `/packets` — deployed MAS **OpenAPI has no `meshtastic` paths** (orchestrator build predates router or different image). **Action:** deploy current `myca_main.py` + `meshtastic_api` to **192.168.0.188** and restart `mas-orchestrator`. |
| **MAS OpenAPI** | `200` on `http://192.168.0.188:8001/openapi.json` |

---

## 3. Operator — broker VM 196 (Mosquitto + bridge)

1. **SSH:** `ssh mycosoft@192.168.0.196` (password from `.credentials.local` only on the operator machine — never commit).
2. **Mosquitto:** `systemctl status mosquitto`; `ss -lntp | grep -E '1883|9001'`; read `/etc/mosquitto/mosquitto.conf` and ACLs — Meshtastic uses `msh/#`; keep Jetson/MDP topics separate.
3. **Copy MAS repo** to `/home/mycosoft/mycosoft-mas` (or sync); `poetry install` to create `.venv`.
4. **Env file:** `sudo install -d /etc/mycosoft`; copy `scripts/vm/meshtastic-bridge.env.example` → `/etc/mycosoft/meshtastic-bridge.env`; `chmod 600`; fill real `MINDEX_INTERNAL_TOKEN` and MQTT user/pass if required.
5. **systemd:** Copy `scripts/vm/mqtt-meshtastic-bridge.service` to `/etc/systemd/system/`; adjust `User`, `WorkingDirectory`, and `ExecStart` if venv path differs; `sudo systemctl daemon-reload && sudo systemctl enable --now mqtt-meshtastic-bridge`.
6. **Logs:** `journalctl -u mqtt-meshtastic-bridge -f` — expect no repeated MINDEX 401/403; fix **196 → 189** firewall if `Connection refused` to MINDEX/Redis.

**MAS VM 188:** Ensure **no** second `mqtt_meshtastic_bridge` process; only **196** should subscribe `msh/#` for this architecture.

**Install helper:** run on **196** after placing repo and env file:

`bash scripts/vm/install_meshtastic_bridge_systemd.sh` (from MAS repo root — prints exact `sudo cp` steps for systemd).

---

## 4. Operator — four LilyGO boards (firmware + MQTT)

Fill this table in the field (reference COMs from your LAN plan: e.g. COM3, 11, 12, 14, 15 — re-check Device Manager per session).

| Board | Variant | Site / role | COM | Firmware pin | MQTT OK |
|-------|---------|-------------|-----|--------------|---------|
| 1 | | | | v2.7.15.567b8ea (example) | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |

**Per board:** Meshtastic Web Flasher or esptool → stock firmware → **Region** + **channel PSK** fleet-wide → MQTT **192.168.0.196:1883** + broker ACL creds → uplink ON → position broadcast interval sane for maps.

---

## 5. Website / localhost verification

1. `WEBSITE/website/.env.local`: `MAS_API_URL=http://192.168.0.188:8001`, `NEXT_PUBLIC_MAS_API_URL` same.
2. After MAS deploy includes `/api/meshtastic`: `GET http://localhost:3010/api/meshtastic/packets?limit=10` → JSON `items`.
3. Open `/natureos/meshtastic/map` — activity overlay when packets carry decoded positions in `payload`.

---

## 6. Optional — registry sidecar (metadata only)

Post periodic HTTP heartbeat from each gateway host (or a small LAN script) to MAS **device registry** with Meshtastic node id + site label — **does not** replace MDP over LoRa; parallel metadata track only. Implement when registry endpoints and labels are fixed.

---

## 7. How to verify

- **Broker:** `mosquitto_sub -h 192.168.0.196 -p 1883 [-u … -P …] -t 'msh/#' -v` (30–120 s).
- **Bridge:** `journalctl` clean; MINDEX `meshtastic` packet rows; Redis `XRANGE mesh:packets - + COUNT 5` on **189**.
- **MAS:** `GET /api/meshtastic/packets?limit=5` returns `200` after deploy.
- **Map:** NatureOS map shows node circles + activity caption when data exists.

---

## 8. Lessons learned

- **Live MAS** may not expose `meshtastic` routes until redeployed; always check `openapi.json` for `/api/meshtastic`.
- **SSH automation** (MCP, Paramiko) requires `VM_PASSWORD` in environment — load `.credentials.local` in the same shell as the tool.
- **TennMesh-style** density is client-side: `MeshMap` + `streamPacketsToSignalGeoJson` + `packetsToLinkGeoJson` with REST packet history when SSE is not on the map route.

---

**Date:** May 03, 2026  
**Status:** Complete (implementation + handoff; field VM/radio steps for operator)
