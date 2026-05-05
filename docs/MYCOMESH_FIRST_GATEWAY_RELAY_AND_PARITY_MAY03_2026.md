# MYCOmesh — first Meshtastic gateway, relays, MycoBrain path, and CoreScope-style parity (May 03, 2026)

**Status:** Operational checklist (hardware + software you run)  
**Related:** `mycosoft_mas/integrations/mqtt_meshtastic_bridge.py`, `mycosoft_mas/integrations/meshtastic_protocol.py`, MINDEX `mindex_api/routers/meshtastic_internal.py`, website `/natureos/meshtastic/*`, external reference UI [CoreScope / TennMesh](https://live.tennmesh.com/#/packets) (feature inspiration only — not a fork).

---

## 1. What “100% like CoreScope” means here

CoreScope is a live Meshtastic observability product (packets table with rich filters, audio lab, nodes, channels, map, perf). **MYCOmesh** targets the same *capabilities* on **your** stack:

| Area | Mycosoft source of truth | Your action |
|------|---------------------------|-------------|
| Packets + decoded text | MINDEX `meshtastic.packets` (`payload`, `payload_text`, RSSI/SNR, hops) | Keep MQTT bridge running; ensure firmware sends text apps |
| Live stream | Redis stream `mesh:packets` → MAS SSE `/api/meshtastic/stream` | Redis reachable from MAS; bridge `_push_stream` includes fields you need |
| Nodes / observers | MINDEX `meshtastic.nodes`, `meshtastic.observers` | Position + nodeinfo ingest from mesh; gateways upsert `gateway_kind` |
| Audio | Website sonification from **real** `payload_text` + RSSI + port (not TTS) | Unmute Audio lab / Live; optional later: browser SpeechSynthesis only if you explicitly want spoken text |
| Map / live | Website `LiveScope` + GeoJSON from packets with lat/lon | Height + GPS on at least one node |

**Gap to close for parity:** advanced CoreScope-only features (expression DSL, BYOP hex editor, custom column layouts) are **not** required for production mesh ops; add only if product asks.

---

## 2. First *direct* Meshtastic gateway (recommended path: MQTT uplink)

This is the fastest way to get RF packets into MINDEX with the code you already have.

### 2.1 Hardware

1. **LoRa Meshtastic device** (examples): RAK WisBlock Meshtastic kit, Heltec V3, T-Beam, or similar **915 MHz** (region-appropriate) hardware with a **good antenna** and stable USB power.
2. Flash **official Meshtastic firmware** for that board from [meshtastic.org](https://meshtastic.org) (or your pinned release).
3. In the Meshtastic app: set **region**, **modem preset**, and a **Primary channel** name + PSK consistent with any relay nodes you add later.

### 2.2 MQTT uplink (gateway role)

1. Choose a broker the handset can reach:
   - **Public:** `mqtt.meshtastic.org` (TLS 8883) — traffic is visible on the public mesh; use for smoke tests only if acceptable.
   - **Private (recommended):** Mosquitto or EMQX on your LAN or VM (e.g. MAS **188** or Sandbox **187**), TLS optional inside LAN.
2. On the Meshtastic device, enable **MQTT** and set host/port/user/pass to match the broker. Enable **JSON / uplink** per Meshtastic docs so **ServiceEnvelope** packets hit topic prefix `msh/#`.
3. Confirm with any MQTT client that you see topics like `msh/US/.../.../channel/!gatewayhex`.

### 2.3 Mycosoft bridge (MAS)

1. On the machine running **`mqtt_meshtastic_bridge`** (typically MAS VM **192.168.0.188**), set environment (names may vary slightly — see bridge module header):
   - `MESHTASTIC_MQTT_HOST`, `MESHTASTIC_MQTT_PORT`, TLS flags, `MESHTASTIC_MQTT_USERNAME` / `MESHTASTIC_MQTT_PASSWORD` if needed.
   - `MINDEX_API_URL` → MINDEX internal base (e.g. `http://192.168.0.189:8000`).
   - `MINDEX_INTERNAL_SECRET` or `MINDEX_INTERNAL_TOKEN` for `X-Internal-Token` on `/api/mindex/internal/meshtastic/ingest/*`.
   - `REDIS_URL` where MAS SSE reads `mesh:packets` (often `redis://192.168.0.189:6379/0`).
2. Run the bridge process (systemd unit or Docker sidecar — follow your existing MAS deploy pattern).
3. Verify:
   - MINDEX: `GET /api/mindex/internal/meshtastic/packets` returns rows.
   - MAS: `GET /api/meshtastic/packets` proxies the same.
   - Website dev: `/natureos/meshtastic/packets` shows time/channel/text/RSSI/SNR/hops when present.

**Decode note:** The bridge now fills `payload_text` from protobuf `decoded.text` when present and forwards it on the Redis stream for live UI + audio lab.

---

## 3. First relays (RF mesh, not servers)

1. Add a **second** Meshtastic node with the **same channel PSK and name** as the gateway handset, correct region, and a clear RF path (height matters).
2. Power it; confirm on the first device’s **node list** that the second node is heard.
3. Send a **text message** on the primary channel; confirm it appears in MINDEX `payload_text` after traversing the mesh.
4. Optionally add a **router** role device in a fixed location to improve coverage (Meshtastic role = `ROUTER` / `REPEATER` per firmware version).

No extra Mycosoft code is required for basic RF relaying — Meshtastic handles store-and-forward.

---

## 4. MycoBrain + LoRa “on this network” (integration, not the same radio stack)

**Important distinction:** MycoBrain firmware today is **not** a Meshtastic radio. Meshtastic uses its own LoRa MAC, channels, and encryption. A MycoBrain board does **not** join a Meshtastic mesh by default.

You have three integration patterns (pick one for v1):

| Pattern | What you build | `gateway_kind` in MINDEX |
|--------|----------------|---------------------------|
| **A. Co-located serial** | Meshtastic node on USB/serial; MycoBrain or a small PC runs a **serial/API forwarder** that POSTs to MAS/MINDEX ingest (custom) | `mycobrain` once you emit our ingest schema |
| **B. Independent sensors** | MycoBrain LoRa speaks **your** MDP protocol; a **gateway** service translates MDP events into mesh packets or sidecar HTTP ingest | `lora` or `mycobrain` |
| **C. MQTT-only** | MycoBrain does not speak Meshtastic; mesh visibility is entirely via Meshtastic MQTT as in §2 | `mqtt` |

**Practical v1:** finish **C** (MQTT gateway + bridge) for mesh parity; in parallel spec **B** MDP opcodes for “forward compressed telemetry” and one **RAK** or **ESP32+SX1262** bridge binary so MycoBrain data **correlates** with mesh time/place in MINDEX (CREP layer follow-up).

---

## 5. MDP pipeline + MINDEX + MAS

1. **Ingest:** already `POST /api/mindex/internal/meshtastic/ingest/packet` (bridge) and related node/observer/route endpoints.
2. **Read path:** MAS `mycosoft_mas/core/routers/meshtastic_api.py` proxies lists and SSE to the website BFF `/api/meshtastic/*`.
3. **MDP:** when MycoBrain sends device payloads to MAS, add a small MAS normalizer that writes **either** Meshtastic-shaped rows (if you want one table) **or** a parallel `mdp.*` schema and CREP links — do not fake mesh packets.

---

## 6. Verification checklist (you run)

- [ ] Two Meshtastic nodes see each other on RF.  
- [ ] MQTT client shows `msh/#` traffic from the gateway.  
- [ ] Bridge logs: no repeated `MINDEX ingest failed`.  
- [ ] MINDEX packets query returns non-zero `payload_text` after a chat message.  
- [ ] Website `/natureos/meshtastic/audio-lab` unmuted: tones fire; **decoded text** changes rhythm/pitch (sonification).  
- [ ] Website `/natureos/meshtastic/channels`: select channel → message list fills from real `payload_text`.  
- [ ] Cloudflare purge + Sandbox deploy only when you ship website changes (your standard pipeline).

---

## 7. Optional: spoken text (not default)

If you want **actual speech** from `payload_text`, add an explicit **user toggle** (“Read messages aloud”) using the browser **Web Speech API**, and only run it when the user opts in — do not autoplay TTS on the public site.

---

## 8. Related docs to keep updated

- `docs/AGARIC_DEVICE_REGISTRY_DEPLOY_HANDOFF_MAY04_2026.md` — when mesh gateways become first-class devices in the registry.  
- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` — IPs for MAS/MINDEX/Redis.
