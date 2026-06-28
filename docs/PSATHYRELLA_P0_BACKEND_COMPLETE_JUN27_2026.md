# Psathyrella P0 Backend Complete — Jun 27, 2026

**Date:** 2026-06-27  
**Status:** Superseded by P0–P6 master status (P0 items remain valid)  
**Master status:** [`PSATHYRELLA_BACKEND_P0_P6_STATUS_JUN27_2026.md`](./PSATHYRELLA_BACKEND_P0_P6_STATUS_JUN27_2026.md)  
**Related spec:** `D:/Users/admin2/Desktop/MYCOSOFT/CODE/docs/PSATHYRELLA_P0_BACKEND_FIRMWARE_SPEC_JUN27_2026.md`  
**Scope:** MAS repo only (website frozen)

---

## Delivered

### P0-1 — Four new MDP handlers (`command_handler.py`)

| Command | Behavior |
|---------|----------|
| `comms.set_bearer` | Validates bearer enum; sets `runtime.preferred_bearer`; calls `comms_bridge.set_bearer` |
| `acoustic.set_gain` | Clamps -12..48 dB; sets `runtime.hydrophone_gain_db`; forwards to device when path exists |
| `mission.upload` | Validates `MissionPlan`; persists to Redis; loads mission executor |
| `mission.abort` | Aborts executor; sets mode `RTL` or `STATION_KEEP` per `comms_loss_policy` |

### P0-2 — Telemetry builder extensions (`telemetry_builder.py`)

- `contactState`, `lastContactMsAgo` (derived from RF + satellite)
- `comms.satellite` (null fields when no hardware)
- `comms.hydrophone.gainDb`, `spectrum` passthrough
- `autonomy.commsLossPolicy`, `autonomy.activeMissionId`
- `propulsion.thrusters[].currentA/rpm/faulted` passthrough from payload
- `chainOfCustody` passthrough on contacts
- `peers`, `mesh` empty defaults (contract shape)

### P0-3 — Command ACK envelope

`POST /api/psathyrella/{id}/command` returns:

```json
{ "ok": true, "cmd": "...", "response": {}, "ack": { "commandId", "seq", "state", "bearer", "acceptedMs", "appliedMs", "latencyMs", "detail" } }
```

Accepts optional `clientCommandId` in POST body.

### P0-4 — Comms bridge (`comms_bridge.py`)

- `set_bearer(device_id, bearer)`
- `select_bearer`, `get_satellite_state`
- mo/mt queue counters in `get_state` (legacy store-forward preserved)

### P0-5 — Mission module (`mission_executor.py`)

- `load_mission_plan`, `validate_mission_plan_dict`, `get_mission_executor`
- Redis key: `psathyrella:mission:{deviceId}`

### P0-6 — Runtime state (`runtime_state.py`)

- `preferred_bearer`, `hydrophone_gain_db`, `comms_loss_policy`, `active_mission_id`
- `derive_contact_state`, `last_contact_ms_ago` helpers

### P0-6 — Tests

16 tests passing:

```powershell
python -m pytest tests/core/test_psathyrella_telemetry.py tests/core/test_psathyrella_bridge.py tests/core/test_psathyrella_autonomy.py tests/core/test_psathyrella_command.py -q
```

---

## Verify on MAS 188

```powershell
Invoke-RestMethod http://192.168.0.188:8001/api/psathyrella/health
Invoke-RestMethod http://192.168.0.188:8001/api/psathyrella/telemetry
```

Example new handler (dry — no device required for bearer set):

```powershell
Invoke-RestMethod -Method POST -Uri "http://192.168.0.188:8001/api/psathyrella/psathyrella-buoy-com4/command" `
  -ContentType "application/json" `
  -Body '{"target":"side_b","cmd":"comms.set_bearer","params":{"bearer":"iridium"},"clientCommandId":"cmd_verify_1"}'
```

Expected: HTTP 200, `"ok": true`, `"ack": { "state": "applied", ... }`.

Invalid bearer → HTTP 400 (not 500):

```powershell
Invoke-RestMethod -Method POST -Uri "http://192.168.0.188:8001/api/psathyrella/psathyrella-buoy-com4/command" `
  -ContentType "application/json" `
  -Body '{"target":"side_b","cmd":"comms.set_bearer","params":{"bearer":"invalid"}}'
```

---

## Hardware-blocked (documented only)

See **`PSATHYRELLA_BACKEND_P0_P6_STATUS_JUN27_2026.md`** for full P0–P6 table. Summary:

- MAVLink/ArduSub ESC wiring and 4-thruster allocation on FC
- Live GPS module publish format (NMEA parser ready in `gps_nmea.py`)
- Camera RTSP streams
- Full bidirectional Iridium SBD codec + fragmentation (budget guard only)
- Hydrophone 48-bin live spectrum (needs edge DSP)
- Edge NLM + Merkle chain-of-custody (hash passthrough only; Merkle omitted)
- Website SSE WS passthrough (Claude/GCS lane — MAS `/stream` is live)

---

## Files changed

| File | Change |
|------|--------|
| `mycosoft_mas/devices/psathyrella/command_handler.py` | +4 handlers, ack envelope |
| `mycosoft_mas/devices/psathyrella/runtime_state.py` | +runtime fields, contact helpers |
| `mycosoft_mas/devices/psathyrella/telemetry_builder.py` | +contract fields |
| `mycosoft_mas/devices/psathyrella/comms_bridge.py` | +set_bearer, mo/mt, satellite |
| `mycosoft_mas/devices/psathyrella/mission_executor.py` | **NEW** |
| `mycosoft_mas/core/routers/psathyrella_api.py` | clientCommandId passthrough |
| `tests/core/test_psathyrella_command.py` | **NEW** |
| `tests/core/test_psathyrella_telemetry.py` | updated shape |
| `tests/core/test_psathyrella_bridge.py` | +set_bearer test |
