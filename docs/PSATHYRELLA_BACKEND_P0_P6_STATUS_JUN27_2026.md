# Psathyrella Backend P0–P6 Status — Jun 27, 2026

**Date:** 2026-06-27  
**Status:** Cursor lane software complete (pool test pending hardware)  
**Related spec:** `D:/Users/admin2/Desktop/MYCOSOFT/CODE/docs/PSATHYRELLA_P0_BACKEND_FIRMWARE_SPEC_JUN27_2026.md`  
**Prior completion:** `docs/PSATHYRELLA_P0_BACKEND_COMPLETE_JUN27_2026.md`  
**Scope:** MAS + MINDEX backend only (GCS/website = Claude lane)

---

## Executive summary

| Phase | Software complete | Notes |
|-------|-------------------|-------|
| **P0** | **100%** | MDP handlers, telemetry contract, ack envelope, comms bridge basics |
| **P1** | **~85%** | SINE register wired; live spectrum/thruster/GPS need firmware |
| **P2** | **~75%** | Bidirectional mo/mt queues + SBD budget guard; no live modem |
| **P3** | **~70%** | Shadow mission executor + geofence/comms-loss ticks; edge mirror hardware |
| **P4** | **~80%** | NLM + TAC-O + chain-of-custody hash on ingest; Merkle edge-blocked |
| **P5** | **~60%** | MAS SSE `/stream` live; website WS passthrough = Claude lane |
| **P6** | **Documented** | Jetson adapter contract only; no MAS Jetson client yet |

**Cursor lane statement:** Software backend for Psathyrella is complete for pool test pending hardware wiring (thrusters, GPS module, hydrophone capture path, cameras, satellite modems).

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
| P5 | MAS SSE `GET /api/psathyrella/{id}/stream` | **DONE** | MAS | Telemetry events @ 2.5s |
| P5 | Website WS passthrough | **DEFERRED** | Claude/GCS | `app/api/psathyrella/ws/route.ts` |
| P6 | Jetson edge adapter | **DOCUMENTED** | Cursor/FW | See § Jetson contract below |
| HW | MAVLink/ArduSub 4-thruster ESC PWM | **HARDWARE-BLOCKED** | Morgan/FW | Pool drive Tier B |
| HW | Live GPS module | **HARDWARE-BLOCKED** | Morgan | GNSS not wired |
| HW | Camera RTSP | **HARDWARE-BLOCKED** | Morgan | Env `PSATHYRELLA_*_STREAM_URL` |
| HW | Iridium/Starlink modems | **HARDWARE-BLOCKED** | Morgan | Bearer software ready |
| HW | Pool leak test / kill switch | **HARDWARE-BLOCKED** | Morgan | Tier B gates |

---

## What Morgan can demo today (Tier A bench)

- MAS `GET /api/psathyrella/health` + `/telemetry` with honest nulls/STANDBY
- BME688 A live when MycoBrain COM3 connected
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

- Claude lane: `app/api/psathyrella/ws/route.ts` SSE passthrough to MAS `/stream`
- Deploy MINDEX 189 with `sine/library/register` before first blob ingest
- Edge Jetson mission executor mirror (authoritative when dark)

---

## Deploy SHA (MAS 188)

**Deployed:** 2026-06-28 UTC  
**git_sha:** `1f8fbf508c364af729ed3b9799507d8f41642a57`  
**Verify:** `Invoke-RestMethod http://192.168.0.188:8001/health | Select-Object status, git_sha`
