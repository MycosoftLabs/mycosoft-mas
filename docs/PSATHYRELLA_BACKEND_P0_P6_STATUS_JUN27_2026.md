# Psathyrella Backend P0–P6 Status — Jun 27, 2026

**Date:** 2026-06-27  
**Status:** Cursor lane software complete (pool test pending hardware)  
**Related spec:** `D:/Users/admin2/Desktop/MYCOSOFT/CODE/docs/PSATHYRELLA_P0_BACKEND_FIRMWARE_SPEC_JUN27_2026.md`  
**Prior completion:** `docs/PSATHYRELLA_P0_BACKEND_COMPLETE_JUN27_2026.md`  
**Scope:** MAS + MINDEX backend (Cursor lane); GCS/website integration = Claude lane (P5 passthrough **closed** Jun 27)

---

## Executive summary

| Phase | Software complete | Notes |
|-------|-------------------|-------|
| **P0** | **100%** | MDP handlers, telemetry contract, ack envelope, comms bridge basics |
| **P1** | **~85%** | SINE register wired; live spectrum/thruster/GPS need firmware |
| **P2** | **~75%** | Bidirectional mo/mt queues + SBD budget guard; no live modem |
| **P3** | **~70%** | Shadow mission executor + geofence/comms-loss ticks; edge mirror hardware |
| **P4** | **~80%** | NLM + TAC-O + chain-of-custody hash on ingest; Merkle edge-blocked |
| **P5** | **~95%** | MAS SSE source live; website SSE passthrough **CLOSED** (Claude lane, Jun 27) |
| **P6** | **~60%** | MAS `jetson_forward.py` live on 188; Jetson `:8787` MDP handler + wiring pending Morgan |

**Cursor lane statement:** Software backend for Psathyrella is complete for pool test pending hardware wiring (thrusters, GPS module, hydrophone capture path, cameras, satellite modems).

---

## Jul 06, 2026 — propulsion live (Claude → Cursor handoff)

- **Hardware:** PCA9685 @ **0x60** (bus 7), direct I2C, **no TXS**; ESC **CH8–11**, servos CH4–7; neutral/stop **1600µs** @ 5V VCC.
- **Repo:** tracked `devices/psathyrella-jetson/jetson_agent.py` + systemd drop-ins mirror live Jetson patches.
- **MAS P0:** `PSATHYRELLA_DEFAULT_BEARER=wifi` on command intake; `nav.thrust_vector` forwards when `:8788` health OK even if contactState is dark; bench wifi counts as RF when `PSATHYRELLA_BENCH_RF_VIA_JETSON=1`.
- **Evidence:** GCS 42-step bench matrix + joystick applied post bearer fix (Claude session Jul 06 evening).
- **Handoff doc:** `CODE/docs/PSATHYRELLA_CURSOR_BACKEND_HANDOFF_JUL06_2026_PROPULSION_LIVE.md`

---

## Jul 03, 2026 backend flip update

- MAS now treats `psathyrella-1` as the canonical public device id for Psathyrella routes.
- `psathyrella-buoy-com4` and `mycobrain-COM4` now resolve to the same MAS backend lane.
- Live MAS verification on `192.168.0.188:8001` now shows `status`, `telemetry`, `stream`, and `openclaw/status` working for `psathyrella-1`.
- `nav.*` forwarding is pinned to propulsion on `http://192.168.0.123:8788` and no longer falls back to Mushroom 1 on `:8787`.
- Jetson propulsion on `:8788` is now live with working `POST /command`, `/state`, and `/selftest`; MAS `nav.pwm_raw` reaches the PCA9685 path end-to-end.
- CH4 (continuous azimuth servo) was live-calibrated on Jul 03 and persisted as `SERVO_STOP_US_CH4=1700` in the Jetson user service so restart + `nav.all_stop` return that channel to neutral.
- Jetson propulsion arm behavior was corrected on Jul 03 so `nav.arm {armed:true}` now comes up at ESC neutral `1500us` instead of replaying stale stored throttle during DD ESC arming.

---

## Phase table

| Phase | Item | Status | Owner | Evidence |
|-------|------|--------|-------|----------|
| P0 | 4 MDP handlers (`comms.set_bearer`, `acoustic.set_gain`, `mission.upload`, `mission.abort`) | **DONE** | MAS | `command_handler.py`, 6 command tests |
| P0 | Telemetry contract fields (`contactState`, satellite, hydrophone, autonomy) | **DONE** | MAS | `telemetry_builder.py`, telemetry tests |
| P0 | Command ack envelope + `clientCommandId` | **DONE** | MAS | `POST /api/psathyrella/{id}/command` |
| P0 | Comms bridge `set_bearer`, mo/mt counters | **DONE** | MAS | `comms_bridge.py` |
| P0 | Mission Redis persistence | **DONE** | MAS | `mission_executor.py` |
| P1 | Thruster telemetry passthrough (`currentA`, `rpm`, `faulted`) | **PARTIAL** | MAS+FW | Builder passthrough; needs ESC publish |
| P1 | GPS NMEA → pose | **PARTIAL** | MAS+FW | `gps_nmea.py`; needs live NMEA on serial |
| P1 | Hydrophone spectrum passthrough | **PARTIAL** | MAS+FW | `_extract_comms`; needs edge DSP |
| P1 | SINE blob ingest | **PARTIAL** | MAS+MINDEX | `sine_ingest.py` → `POST /api/mindex/sine/library/register` |
| P1 | `ingest_acoustic` → NLM + TAC-O | **DONE** | MAS | `psathyrella_api.py` comms action |
| P2 | Bidirectional MT/MO queues + flush | **DONE** | MAS | `enqueue_mt_command`, `flush_mt_queue`, `flush_mt` action |
| P2 | Iridium SBD framing | **PARTIAL** | MAS | `pack_sbd_frame` budget guard only |
| P2 | Satellite telemetry stub | **DONE** | MAS | Null fields until modem |
| P3 | Mission executor behavior tree | **PARTIAL** | MAS+Edge | `tick()` transit/loiter/survey/track/station_keep |
| P3 | Geofence + comms-loss alerts | **PARTIAL** | MAS+Edge | Shadow on MAS; edge authoritative when dark |
| P4 | Chain-of-custody on acoustic ingest | **PARTIAL** | MAS | SHA-256 hash when NLM ok; Merkle omitted |
| P5 | MAS SSE `GET /api/psathyrella/{id}/stream` | **DONE** | MAS | Backend source of truth; telemetry events @ 2.5s |
| P5 | Website SSE passthrough `/api/psathyrella/stream` → MAS `/stream` | **CLOSED** | Claude/GCS | Jun 27 — EventSource in `useBuoyTelemetry`; live verified (SSE, not WS) |
| P6 | Jetson edge adapter | **PARTIAL** | Cursor/FW | `jetson_forward.py` on MAS 188; Jetson `:8787` HTTP handler pending |
| HW | MAVLink/ArduSub 4-thruster ESC PWM | **HARDWARE-BLOCKED** | Morgan/FW | Pool drive Tier B |
| HW | **Physical wiring plan (12 V, PCA9685, ESC, kill switch)** | **DOC READY** | Morgan/FW | `CODE/docs/PSATHYRELLA_HARDWARE_WIRE_PLAN_JUL01_2026.md` — Tier A bench + Tier B pool; **azimuth = FS90MR (360°)**; MG996R → Mushroom 1/Agaric |
| HW | **CEO procurement briefing (buy now / do not buy)** | **DOC READY** | Morgan | `CODE/docs/PSATHYRELLA_PROCUREMENT_BRIEFING_JUL01_2026.md` — ASIN cart, power chain, Jul 1 movement NO-GO |
| HW | Live GPS module | **HARDWARE-BLOCKED** | Morgan | GNSS not wired |
| HW | Camera RTSP | **HARDWARE-BLOCKED** | Morgan | Env `PSATHYRELLA_*_STREAM_URL` |
| HW | Iridium/Starlink modems | **HARDWARE-BLOCKED** | Morgan | Bearer software ready |
| HW | Pool leak test / kill switch | **HARDWARE-BLOCKED** | Morgan | Tier B gates |

---

## What Morgan can demo today (Tier A bench)

- MAS `GET /api/psathyrella/health` + `/telemetry` with honest nulls/STANDBY
- BME688 A live when **Mushroom 1** on Jetson `:8787` / MQTT `psathyrella-1` is reachable
- `comms.set_bearer iridium` → ledger **APPLIED** (ack envelope)
- Mission upload/abort without 502
- `GET /api/psathyrella/psathyrella-buoy-com4/stream` SSE telemetry snapshots
- SINE widget STANDBY until first hydrophone blob registered on MINDEX NAS path

## After pool wiring (Tier B)

- Thruster motion + non-null `propulsion.thrusters[].currentA|rpm`
- GPS `pose.gpsLock: "locked"`
- One hydrophone clip → SINE register + analyze
- Camera still or RTSP frame in GCS

---

## Cross-lane coordination (Jun 27, 2026)

| Lane | Owner | Status doc |
|------|-------|------------|
| Backend / MAS / MINDEX | Cursor | This file |
| GCS front-end + sim | Claude | `D:/Users/admin2/Desktop/MYCOSOFT/CODE/docs/PSATHYRELLA_GCS_P0_P6_INTEGRATION_STATUS_JUN27_2026.md` |

**Aligned this session:**

- **P5 stream:** Claude shipped website SSE passthrough (`/api/psathyrella/stream` → MAS 188 `GET /api/psathyrella/{id}/stream`); GCS `useBuoyTelemetry` consumes via EventSource. Backend SSE endpoint remains the authoritative source.
- **Bearer policy:** GCS demo defaults to **cellular** as primary C2 (pool Tier B); LoRa secondary; satellite STANDBY — matches Cursor pool-drive guidance (not LoRa-primary for pool test). CommsPanel set-bearer control issues `comms.set_bearer` to MAS.
- **Map selectability:** AssetInteractions hover + click detail cards shipped on GCS map (Earth-Sim parity); GCS-only, no MAS change.

**Pool test still waits on hardware:** GPS module, 4G backhaul wiring, thruster ESC + kill switch — software lanes synced; field demo blocked until Morgan bench/pool install.

---

## Jetson / edge adapter contract (P6 — document only)

Edge agent (Jetson :8787 or MycoBrain gateway) should publish into MycoBrain telemetry JSON:

```jsonc
{
  "gps": { "lat", "lon", "heading_deg", "speed_kn", "satellites", "lock" },
  "propulsion": { "thrusters": [{ "id", "throttle_pct", "current_a", "rpm", "faulted" }] },
  "comms": { "hydrophone": { "level_db", "peak_bearing_deg", "gain_db", "spectrum": [/* 48 bins */] } },
  "timestamp": "ISO-8601"
}
```

NMEA lines may appear in serial raw text; MAS `gps_nmea.py` merges GGA/RMC into `gps`. Mission executor on edge is authoritative when `contactState === "dark"`.

---

## Verification commands (no secrets)

```powershell
# MAS health + telemetry
Invoke-RestMethod http://192.168.0.188:8001/api/psathyrella/health
Invoke-RestMethod http://192.168.0.188:8001/api/psathyrella/telemetry

# Bearer command + ack
Invoke-RestMethod -Method POST -Uri "http://192.168.0.188:8001/api/psathyrella/psathyrella-buoy-com4/command" `
  -ContentType "application/json" `
  -Body '{"target":"side_b","cmd":"comms.set_bearer","params":{"bearer":"iridium"},"clientCommandId":"cmd_verify_1"}'

# SSE stream (first event)
curl -N -H "Accept: text/event-stream" http://192.168.0.188:8001/api/psathyrella/psathyrella-buoy-com4/stream

# MINDEX SINE register (after hydrophone file on NAS mount at 189)
Invoke-RestMethod -Method POST -Uri "http://192.168.0.189:8000/api/mindex/sine/library/register" `
  -ContentType "application/json" `
  -Body '{"abs_path":"/path/on/mindex/nas/recording.wav","source_id":"psathyrella-psathyrella-buoy-com4-hydrophone","sensor_type":"hydrophone","acoustic_domain":"water","device_id":"psathyrella-buoy-com4","duration_sec":12.0,"metadata":{"tags":["psathyrella","hydrophone","water"]}}'

# Unit tests (local)
cd MAS/mycosoft-mas
python -m pytest tests/core/test_psathyrella_telemetry.py tests/core/test_psathyrella_bridge.py tests/core/test_psathyrella_autonomy.py tests/core/test_psathyrella_command.py tests/core/test_psathyrella_mission_gps.py tests/core/test_psathyrella_sine_ingest.py -q
```

---

## Files changed (this session)

| File | Change |
|------|--------|
| `mycosoft_mas/devices/psathyrella/gps_nmea.py` | **NEW** NMEA GGA/RMC parser |
| `mycosoft_mas/devices/psathyrella/sine_ingest.py` | Real MINDEX register + analyze client |
| `mycosoft_mas/devices/psathyrella/comms_bridge.py` | MT/MO flush, SBD budget guard |
| `mycosoft_mas/devices/psathyrella/mission_executor.py` | `tick()`, geofence, task advance |
| `mycosoft_mas/devices/psathyrella/telemetry_builder.py` | NMEA merge, registry heartbeat contact |
| `mycosoft_mas/devices/psathyrella/command_handler.py` | MT queue on dark, `psa_gps_passthrough` |
| `mycosoft_mas/core/routers/psathyrella_api.py` | SSE `/stream`, SINE on ingest, chain-of-custody |
| `MINDEX/mindex_api/routers/sine_acoustic.py` | `POST /sine/library/register` |
| `tests/core/test_psathyrella_mission_gps.py` | **NEW** |
| `tests/core/test_psathyrella_sine_ingest.py` | **NEW** |

**Tests:** 24 passing (psathyrella suite)

---

## Next actions (hardware install sequence)

See `D:/Users/admin2/Desktop/MYCOSOFT/CODE/docs/PSATHYRELLA_PERPLEXITY_POOL_DRIVE_REQUIREMENTS_JUN27_2026.md`:

1. Wire 4 ESCs + kill switch (Tier B2/B5)
2. Connect GPS → verify NMEA on COM3 raw (Tier B4)
3. Hydrophone record → NAS path → SINE register (Tier B7)
4. Camera RTSP or still (Tier B8)
5. Pool test log + command ledger export (Tier B9)

**Software follow-ups (non-hardware):**

- ~~Claude lane: website SSE passthrough to MAS `/stream`~~ **CLOSED Jun 27** (see Cross-lane coordination)
- Deploy MINDEX 189 with `sine/library/register` before first blob ingest
- Edge Jetson mission executor mirror (authoritative when dark)
- Claude lane open items: classification banner, device doc page, OEI/Jetson panels — see GCS integration status doc

---

## Deploy SHA (MAS 188)

**Deployed:** 2026-06-28 UTC (hot-patch overlay on `f69fd3ea`)  
**git_sha (health):** `f69fd3ea375c29d0066b29ee3842c30cd44ee99d`  
**Overlay files (not yet on origin/main):** `jetson_forward.py`, updated `command_handler.py`, `device_registry_api.py`  
**Verify:** `Invoke-RestMethod http://192.168.0.188:8001/health | Select-Object status, git_sha`  
**Live test:** `nav.thruster {id:0, throttle:35, azimuth:90}` → `relay: device_registry`, telemetry `throttlePct:35`, `azimuthDeg:90`

---

## NVIDIA terminology + comms architecture (Jun 28, 2026)

**CEO correction:** Do not use **OpenCL** (GPU compute API) for the NVIDIA agent stack. Use **OpenClaw**, **NemoClaw**, **OpenShell**, **Nemotron**, **NIM** as defined in the new reference docs.

| Doc | Purpose |
|-----|---------|
| `CODE/docs/PSATHYRELLA_JETSON_AGENT_COMMS_QUICKREF_JUN28_2026.md` | **Bench quick-ref (Claude lane):** `:8787` MDP vs `:18789` OpenClaw/NemoClaw, motor curl examples, hardware wiring table, uplink paths |
| `CODE/docs/PSATHYRELLA_HARDWARE_WIRE_PLAN_JUL01_2026.md` | **Hardware wiring plan:** component matrix, Tier A/B wire tables, ESC arming, power budget, PCA9685 channel map, kill switch |
| `CODE/docs/PSATHYRELLA_PROCUREMENT_BRIEFING_JUL01_2026.md` | **CEO procurement briefing:** buy-now ASINs, do-not-buy, power wiring order, tonight checklist, movement NO-GO |
| `docs/NVIDIA_NEMOCLAW_NEMOTRON_NIM_LANDSCAPE_JUN28_2026.md` | Team glossary: NemoClaw (GTC 2026), Nemotron 3, NIM, Ollama vs Meta/Llama clarification |
| `docs/PSATHYRELLA_JETSON_MYCOBRAIN_COMMS_ARCHITECTURE_JUN28_2026.md` | Canonical buoy downlink/uplink, Mushroom 1 `:8787` MQTT vs propulsion split, pool test wiring |
| `CODE/docs/PSATHYRELLA_JETSON_PROP_TEST_JUN28_2026.md` | Jetson handler implementation options (Option A/B), env table, verification curls |

**Cross-doc alignment (Jun 28):** Claude quickref reviewed against MAS architecture + NIM landscape + prop test doc — **no port/IP/command/wiring conflicts**. Shared contract: propulsion MDP on Jetson `192.168.0.123:8787` (extend or split); Mushroom 1 sensors/MQTT on same host `:8787`; MAS forward via `jetson_forward.py`; **not** dev-desk COM3.

**Doc refresh note:** Executive summary P6 row (“no MAS Jetson client yet”) is stale — `jetson_forward.py` is deployed on MAS 188 overlay (see Deploy SHA below); remaining gap is **Jetson-side `:8787` HTTP handler** (Morgan firmware task).

**Grep note:** No literal `OpenCL` typos found under MAS or `CODE/docs` Psathyrella/NemoClaw paths (Jun 28). Fixed `CODE/docs/PSATHYRELLA_JETSON_PROP_TEST_JUN28_2026.md` env table: Jetson `:8787` MDP agent was mislabeled as OpenClaw host.

---

## Movement readiness — Jul 1, 2026

**Go/no-go for Tier A bench (1 ESC, props off): GO for propulsion software path on split-port Option B (`:8788`), with props-off bench precautions.**

| Check | Jul 1 live result |
|-------|-------------------|
| MAS `GET /health` + `/api/psathyrella/health` | **OK** (188 reachable) |
| Mushroom 1 Jetson `GET :8787/status` | **Expected** — MycoBrain agent, role `mushroom1`, MQTT connected; device id **`psathyrella-1`** |
| Jetson propulsion `GET :8788/health` + `POST /command` | **OK** — split-port `psathyrella-agent` active on Jetson |
| MAS `nav.thruster` / `nav.pwm_raw` forward | **OK** — shows `relay: jetson_mdp` to `http://192.168.0.123:8788` |
| `jetson_agent.py` (PCA9685 PWM) | **LIVE** — coexists with Mushroom 1; `/state` confirms PCA9685 writes |
| Mushroom 1 / firmware | **Sensors only** on `:8787` MQTT — does not execute `nav.thruster` |
| Hardware wire plan | **DOC READY** — `PSATHYRELLA_HARDWARE_WIRE_PLAN_JUL01_2026.md` |
| GCS command + SSE | **OK** — Claude lane closed P5; commands reach MAS |
| CH4 neutral trim | **OK** — persisted as `SERVO_STOP_US_CH4=1700` after live bench calibration |
| ESC arm neutral behavior | **OK** — `nav.arm` now holds `CH0=1500us` until throttle is explicitly commanded |

**Current software state:** Propulsion MDP is coexisting cleanly with Mushroom 1 using split-port Option B. **Do not** remove Mushroom 1 from `:8787`; keep propulsion on **`:8788`** with `PSATHYRELLA_PROPULSION_AGENT_URL` pointed at that service.

**Tonight minimum to spin one motor (software + hardware):**

1. **Software:** Confirm Mushroom 1 on `:8787`; keep propulsion on split-port `:8788`; verify MAS `nav.thruster` / `nav.pwm_raw` → `relay: jetson_mdp`.
2. **Hardware:** LiFePO4 + **12→5 V buck** + **UBEC** + fused 12 V to ESC; PCA9685 on Jetson I2C (`0x40`); ESC Yellow/White to CH0; props **off**; kill switch open.
3. **Sequence:** neutral PWM → connect ESC signal → DD arming beeps → `nav.arm` → low `nav.thruster` jog → `nav.all_stop`.

**Can Morgan spin TODAY if they wire bench tonight?** Yes for props-off bench validation, because propulsion MDP on Jetson is now live. Remaining risk is hardware-side only: power path, ESC wiring/arming, and safe bench procedure.

---

## Device lane correction — Jul 01, 2026

**CEO correction (Morgan):** Psathyrella **does not** use dev-desk **MycoBrain on COM3** or local `:8003` service as primary sensor path. **Mushroom 1** on **Jetson `192.168.0.123:8787`** is the sensor/telemetry lane (HTTP + MQTT, device id **`psathyrella-1`**).

| Lane | Correct | Wrong / deprecated |
|------|---------|------------------|
| Sensors | Mushroom 1 → Jetson `:8787` → MQTT `mycosoft/devices/psathyrella-1/...` | COM3 dev desk, `psathyrella-buoy-com4` as hardware id |
| Propulsion | Jetson MDP via `jetson_forward.py` (extend `:8787` or split `:8788`) | Expecting COM3/local service to drive ESC |
| Port 8787 | Mushroom 1 **intentional** — coexist or split propulsion | "Evict operator from 8787" |

**MAS code touch:** `mycosoft_mas/devices/psathyrella/constants.py` — `PSATHYRELLA_CANONICAL_DEVICE_ID=psathyrella-1`, `PSATHYRELLA_MUSHROOM1_AGENT_URL=http://192.168.0.123:8787`.

---

## Lag fix + azimuth home — Jul 07, 2026

**Status: Complete (MAS `7536f553e` on 188, Jetson agent synced)**

| Item | Result |
|------|--------|
| MAS keep-alive HTTP client (`jetson_forward.py`) | **Deployed** — repeated `nav.thrust_vector` ~13–15 ms after warm-up (was ~1080 ms cold TCP) |
| `nav.az_zero` MAS allowlist + handler | **Deployed** — `POST /api/psathyrella/psathyrella-1/command` → `ack.state=applied`, not `unsupported_mdp_command` |
| `nav.az_zero` in tracked `jetson_agent.py` | **Committed + synced** to Jetson `:8788` via `scripts/_sync_jetson_propulsion_agent.py` |
| GCS bench calibration (Claude lane) | **Already live** — direct proxy + Bench "Azimuth · Home / Center" UI |

**Verification (Jul 07):**

- MAS health: `git_sha=7536f553e0c4fa85ff0777d9dfbccfe2cacac9df`
- `nav.az_zero` → `detail: azimuth home set for [0, 1, 2, 3]`, all pods `azimuth_deg=0`
- Latency sample (5× `nav.thrust_vector`): 3191 ms (cold), then 15 / 13 / 13 / 14 ms

**Completion doc:** `docs/PSATHYRELLA_LAG_AZ_ZERO_COMPLETE_JUL07_2026.md`

**Still P1 (hardware only):** AS5600 closed-loop azimuth encoders.

**P1 software (Jul 07):** Complete — see `docs/PSATHYRELLA_P1_COMPLETE_JUL07_2026.md` (ESC cal, per-ESC neutral, PCA re-probe, registry keepalive, INA226/leak hooks). MAS `000412638` deployed; keepalive call-site fix in `8577a5b70+`.

