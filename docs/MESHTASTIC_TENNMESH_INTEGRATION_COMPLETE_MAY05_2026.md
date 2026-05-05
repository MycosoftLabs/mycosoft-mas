# Meshtastic TennMesh + LAN MQTT — integration complete (May 05, 2026)

**Status:** Backend chain verified on LAN; **bridge code** aligned with MAS MINDEX URL rules; **operator-only** steps remain for LilyGO flash, per-radio MQTT, and optional broker ACL smoke tests.

**Plans:** [meshtastic_tennmesh_map_integration_58c0b3f3.plan.md](file:///C:/Users/admin2/.cursor/plans/meshtastic_tennmesh_map_integration_58c0b3f3.plan.md), [meshtastic_lan_mqtt_integration_78ae6738.plan.md](file:///C:/Users/admin2/.cursor/plans/meshtastic_lan_mqtt_integration_78ae6738.plan.md).

**Related docs:** [MESHTASTIC_MAS_MINDEX_CHAIN_VERIFY_MAY05_2026.md](MESHTASTIC_MAS_MINDEX_CHAIN_VERIFY_MAY05_2026.md), [MESHTASTIC_TENNMESH_INTEGRATION_COMPLETE_MAY03_2026.md](MESHTASTIC_TENNMESH_INTEGRATION_COMPLETE_MAY03_2026.md).

---

## 1. Delivered in repo (May 05, 2026)

| Change | Purpose |
|--------|---------|
| `mycosoft_mas/integrations/mqtt_meshtastic_bridge.py` | **`_mindex_internal_meshtastic_base()`** — same normalization as `meshtastic_api._mindex_meshtastic_base()` so `MINDEX_API_URL` may be `http://host:8000` or `.../api/mindex` without double path segments on ingest POSTs. |

MAS orchestrator already used this pattern on **GET** proxies; the **MQTT bridge** is the other critical client posting to `/internal/meshtastic/*`.

---

## 2. VM verification (May 05, 2026)

| Check | Result |
|-------|--------|
| **MAS** `GET http://192.168.0.188:8001/api/meshtastic/stats` | **200** JSON (`node_count` / `packets_*` / `observers_online` — zeros until RF ingest). |
| **VM 188** | **No** `mqtt_meshtastic_bridge` process (`ps aux \| grep` no match). |
| **VM 196** `mqtt-meshtastic-bridge.service` | **active**; journal: Redis **192.168.0.189:6379**, MQTT **127.0.0.1:1883**, subscribed **`msh/#`**, TLS off. |
| **VM 196** `systemctl is-active mosquitto` | Returned **inactive** in one check — broker still accepts the bridge on **localhost:1883** (listener may be another unit, Docker, or legacy init). **Ops:** confirm canonical Mosquitto unit name with `systemctl list-units '*mosquitto*'` on **196**. |

---

## 3. Website (no code change this session)

NatureOS map stack was delivered per **May 03** completion doc (`lib/meshtastic/*`, `hooks/use-meshtastic-packets.ts`, `MeshtasticMeshMapWithActivity`, `/natureos/meshtastic/map`). Local proxy check: `MAS_API_URL` → **188** in `.env.local`, then `GET http://localhost:3010/api/meshtastic/packets` when dev server runs.

---

## 4. Operator backlog (physical / optional)

| Item | Owner |
|------|--------|
| Pin firmware **v2.7.15.567b8ea**, flash four LilyGO boards, align region / channel PSK / MQTT uplink to **192.168.0.196:1883** | Morgan / lab |
| `mosquitto_sub -h 192.168.0.196 -p 1883 -t 'msh/#'` when radios uplink | Ops |
| Confirm **MINDEX** `meshtastic_mesh_packets` rows and **Redis** `XRANGE mesh:packets` once traffic flows | Ops |
| Optional **gateway heartbeat** to MAS device registry (metadata) | Later |

---

## 5. Deploy bridge URL fix on VM 196

After `git pull` on the MAS checkout used by the systemd unit:

```bash
sudo systemctl restart mqtt-meshtastic-bridge
# or: meshtastic-mqtt-bridge — match the installed unit name
```

Ensure `/etc/mycosoft/meshtastic-bridge.env` (or unit `EnvironmentFile`) sets **`MINDEX_API_URL`** consistently with VM **188** / **189** (either style is now accepted).

---

## 6. Secrets

Never commit SSH passwords or internal tokens. Use `.credentials.local` (gitignored) and VM env files only.
