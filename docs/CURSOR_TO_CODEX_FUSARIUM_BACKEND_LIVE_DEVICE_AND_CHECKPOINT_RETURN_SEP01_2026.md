# Cursor to Codex — Fusarium Backend Live Device and Checkpoint Return

**Date:** September 1, 2026  
**Classification:** Commercial UNCLASSIFIED  
**Lane:** Cursor backend only  
**MAS branch:** `cursor/field-operator-live-observations-sep01`  
**MAS commit:** `45bd586bd38d0f518747fcf3a64ffcd6d3efc650` (`45bd586bd`)

## Verdict

**Hyphae 1 is reachable.** Mushroom 1 is not. One real field-device read was obtained from documented operator GET endpoints. Shared board MDP `mycobrain-sidea-10b41d` does not distinguish deployments and was never used as the selectable identity.

## Reachable / unreachable sources

| Source | Identity | Result |
|---|---|---|
| Operator `GET http://192.168.0.228:8787/api/status` | Hyphae 1 host | **HTTP 200**, `serialConnected=true`, `serialPort=/dev/ttyACM0` |
| Operator `GET http://192.168.0.228:8787/api/sensor` | Hyphae 1 host | **HTTP 200**, slots `env` and `amb` |
| Operator `GET http://192.168.0.123:8787/api/status` | Mushroom 1 host | **Timeout** |
| Operator `GET http://192.168.0.123:8787/api/sensor` | Mushroom 1 host | **Timeout** |
| Operator `/health` and `/api/health` on both hosts | n/a | Not documented sensor paths. Hyphae returned HTTP 404; Mushroom 1 timed out. |
| Local MycoBrain `GET http://127.0.0.1:8003/health` | service | HTTP 200, `devices_connected=0`, `timestamp=2026-09-01T22:33:32.632524` |
| Local MycoBrain `GET http://127.0.0.1:8003/devices` | service list | HTTP 200, `devices=[]`, `count=0` |
| MAS `GET http://192.168.0.188:8001/api/devices` | heartbeat registry | HTTP 200, **3 gateway services only** (`mycobrain-service-192-168-0-187`, `-196`, `-241`). No Mushroom 1 / Hyphae 1 registry rows. No sensor telemetry. |
| MAS `GET /api/devices/{registry_id}` and `/telemetry` on live 188 | `mycobrain-hyphae1-jetson-228`, `mycobrain-mushroom1-jetson-123`, catalog aliases, shared MDP | **HTTP 404** on the running revision (new Cursor contract is not deployed) |
| MINDEX `GET /api/mindex/telemetry/samples?device_slug=...` | same IDs | **HTTP 401 Unauthorized**. No samples were read. No credentials were printed or used. |

Service restarts were not performed. 8003 was already up; it was not started or restarted.

## Hyphae 1 — exact accepted observation (as returned)

**Deployment identity (catalog, not guessed from board ID):**

- `registry_id`: `mycobrain-hyphae1-jetson-228`
- `catalog_id`: `hyphae-1`
- `name`: Hyphae 1
- `role`: `hyphae1`
- `host_ip`: `192.168.0.228`
- `agent_url`: `http://192.168.0.228:8787`

**Board-reported identifier (evidence only, shared with Mushroom 1):**

- `device_id` / `node_id`: `mycobrain-sidea-10b41d`
- `role`: `side_a`
- `fw_version`: `recovery-operator-bsec2-v0.7`

**Operator status fields (GET `/api/status`, first successful read):**

- `lastHeartbeat`: `2026-09-02T05:34:01.843Z`
- `identityVerified`: **absent** → treated as not verified

**Latest captured sensor GET (`/api/sensor`, HTTP 200 at probe time):**

Slot `env`:

- `sensor_slot`: `env`
- `address`: `0x76`
- `ts` / observation time: `2026-09-02T05:38:25.167Z`
- `ts_ms`: `363437`
- `valid`: `true`
- `temperature_c_comp`: `25.09` °C (`ambient_temperature_c`: `25.15`)
- `humidity_pct_comp`: `48.38` %RH
- `pressure_hpa`: `647.21` hPa
- `gas_resistance_ohm`: `466834` Ω
- `iaq`: `50` (IAQ index)
- `eco2_ppm`: `500` ppm
- `bvoc_ppm`: `0.5` ppm
- `gas_resistance_ohm_comp`: `null` (not fabricated)

Slot `amb`:

- `sensor_slot`: `amb`
- `address`: `0x77`
- `ts`: `2026-09-02T05:38:25.162Z`
- `temperature_c_comp`: `24.33` °C
- `humidity_pct_comp`: `55.06` %RH
- `pressure_hpa`: `710.17` hPa
- `gas_resistance_ohm`: `490656` Ω
- `iaq`: `50`, `eco2_ppm`: `500`, `bvoc_ppm`: `0.5`

**Provenance:** `source=operator-http`, `status_url=http://192.168.0.228:8787/api/status`, `sensor_url=http://192.168.0.228:8787/api/sensor`.

**Rejected / withheld fields:**

- Shared MDP as selectable device ID
- `identity_verified` (operator did not return `identity_verified` and status did not return `identityVerified`)
- Null `gas_resistance_ohm_comp`, null location lat/lon
- Mushroom 1: no readings (timeout is the evidence)

## Canonical backend contract Senses Overview should consume

Existing planes that **do not** currently carry these field readings:

- `/api/mycobrain/devices` → local 8003 empty list
- MAS heartbeat `/api/devices` → gateway services only, no telemetry
- MINDEX samples → unauthorized in this lane (401)
- `mycosoft_mas/devices/mushroom1.py` `read_sensors()` → **hardcoded mock values; do not use**

Existing Fusarium BFF `GET /api/mycobrain` already probes the two operator hosts and maps `device_id` to `registry_id`. That tree was **not edited**. Codex’s live adapter still:

- uses `liveReadDeviceIds = registry_id` when MDP is shared (correct)
- **rejects** `/api/mycobrain?` rows unless `verified === true` (Hyphae operator is not identity-verified)
- **rejects** `source_device_id` equal to the shared MDP

**New MAS contract (this lane, not deployed to 188):**

- `GET /api/devices/field-operators` — identities only
- `GET /api/devices/field-operators/observations?device_id=<registry_id|catalog_id>`
- `GET /api/devices/{registry_id|catalog_id}/telemetry` — same probe; **HTTP 409** if `device_id=mycobrain-sidea-10b41d`

Selectable `device_id` is always `mycobrain-hyphae1-jetson-228` or `mycobrain-mushroom1-jetson-123`. Board ID is `reported_device_id` only. `source_device_id` is omitted so the shared MDP cannot steal the match.

## Files changed

Owning repo: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`  
Branch: `cursor/field-operator-live-observations-sep01`

| File | Change |
|---|---|
| `mycosoft_mas/devices/field_operator_observations.py` | added — catalog, fail-closed normalizer, GET collector |
| `mycosoft_mas/core/routers/device_registry_api.py` | added field-operator GET routes; telemetry/get fallback |
| `tests/test_field_operator_observations.py` | added — 9 contract tests on captured Hyphae JSON |
| `docs/CURSOR_TO_CODEX_FUSARIUM_BACKEND_LIVE_DEVICE_AND_CHECKPOINT_RETURN_SEP01_2026.md` | this report |

**Not changed:** Codex Fusarium working tree, Earth Simulator, Life Database, NatureOS payloads, website, firmware, services, credentials.

## Tests

```
python -m pytest tests/test_field_operator_observations.py -v --tb=short
```

**9 passed**, 0 failed (2026-09-01 local run).

Covered: unique registry IDs, captured Hyphae provenance, shared-MDP rejection, unreachable Mushroom 1 stays empty, missing timestamp/slot fail-closed, no fabricated humidity when absent.

## Residual blockers

1. Live MAS 188 still serves the old revision. This lane forbade restart/deploy, so public 188 endpoints still 404 for field-operator IDs until a later authorized deploy.
2. Codex Senses adapter will still withhold `/api/mycobrain?` rows while `verified !== true`. Consume the new MAS observations/telemetry shape, or accept unverified-but-timestamped operator rows without inventing `verified=true`.
3. MINDEX history remains unread (401). No sample was assumed.
4. Mushroom 1 operator `192.168.0.123:8787` remains unreachable.
5. `mushroom1.py` still contains mock `read_sensors()` values. Unused by this contract.

## Attestation

- No hardware actuation
- No serial commands
- No firmware changes
- No service restarts (including 8011/8012/8003)
- No deploy, no data migration
- No Codex Fusarium code edits or staging
- No credentials printed (MINDEX 401 reported as status only)
- No fabricated temperatures, humidity, VOC, or tracks

## Paste-ready return prompt for Codex

```
Cursor backend lane returned 2026-09-01.

Hyphae 1 is reachable at GET http://192.168.0.228:8787/api/status and /api/sensor.
Use deployment identity mycobrain-hyphae1-jetson-228 (catalog hyphae-1). Do not select mycobrain-sidea-10b41d; that MDP is shared with Mushroom 1.

Latest captured Hyphae /api/sensor (copy as returned):
- env @ 0x76 observed_at 2026-09-02T05:38:25.167Z temperature_c_comp 25.09 humidity_pct_comp 48.38 pressure_hpa 647.21 gas_resistance_ohm 466834 iaq 50 eco2_ppm 500 bvoc_ppm 0.5 valid true
- amb @ 0x77 observed_at 2026-09-02T05:38:25.162Z temperature_c_comp 24.33 humidity_pct_comp 55.06 pressure_hpa 710.17
Board-reported device_id mycobrain-sidea-10b41d. identity_verified absent. serialPort /dev/ttyACM0 serialConnected true.

Mushroom 1 http://192.168.0.123:8787 /api/status and /api/sensor timed out. Local 8003 /devices is empty. Live MAS /api/devices lists only gateway services. MINDEX samples returned 401; unread.

MAS branch cursor/field-operator-live-observations-sep01 adds GET /api/devices/field-operators/observations and GET /api/devices/{registry_id}/telemetry that preserve registry_id, sensor_slot, address, ts, units, and operator provenance, fail closed when unbound/unreachable, and omit source_device_id for the shared MDP. 9/9 tests passed. Not deployed (restart/deploy forbidden). Do not set verified=true without operator identityVerified.

Cursor did not edit Fusarium, did not actuate, did not send serial, did not change firmware, did not restart services, and did not fabricate readings.
```
