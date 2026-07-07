# Psathyrella P1 Bench Features — Complete

**Date:** Jul 07, 2026  
**Status:** Complete  
**Related:** `CODE/docs/PSATHYRELLA_CURSOR_BACKEND_HANDOFF_JUL06_2026_PROPULSION_LIVE.md` §6, `docs/PSATHYRELLA_LAG_AZ_ZERO_COMPLETE_JUL07_2026.md`

---

## Scope (Cursor P1 list)

| # | Item | Delivered |
|---|------|-----------|
| 1 | ESC throttle-range calibration (`nav.esc_calibrate`) | Jetson agent + MAS allowlist + handler |
| 2 | Per-ESC neutral trim env | `ESC_NEUTRAL_US_BY_CHANNEL`, `ESC_NEUTRAL_US_CH{n}` |
| 3 | PCA background re-probe | `PCA_REPROBE_S` (default 5s) until chip online |
| 4 | Registry heartbeat / no bench expiry | Keepalive loop + `PSATHYRELLA_BENCH_REGISTRY_PERSIST` |
| 5 | INA226 / kill-switch / leak telemetry hooks | `PowerTelemetry`, `LEAK_GPIO`, merged in `/state` + MAS telemetry |

**Hardware still open:** AS5600 closed-loop azimuth (magnetic encoders on P1 hardware list).

---

## Files changed

| Area | Path |
|------|------|
| Jetson agent | `devices/psathyrella-jetson/jetson_agent.py` |
| MAS forward allowlist | `mycosoft_mas/devices/psathyrella/jetson_forward.py` |
| MAS command handler | `mycosoft_mas/devices/psathyrella/command_handler.py` |
| Registry keepalive | `mycosoft_mas/devices/psathyrella/registry_keepalive.py` |
| Registry TTL skip | `mycosoft_mas/core/routers/device_registry_api.py` |
| Constants | `mycosoft_mas/devices/psathyrella/constants.py` |
| Telemetry merge | `mycosoft_mas/devices/psathyrella/telemetry_builder.py` |
| MAS startup | `mycosoft_mas/core/myca_main.py` |
| Tests | `tests/core/test_psathyrella_p1_jul07.py` |

---

## New Jetson commands / env

### `nav.esc_calibrate`

```json
{"cmd":"nav.esc_calibrate","params":{"dry_run":true}}
{"cmd":"nav.esc_calibrate","params":{"id":0,"hold_s":2}}
```

DD sequence per ESC: full forward → full reverse → neutral. **Disarmed only.** Use `dry_run:true` first on bench.

### Per-ESC neutral trim

```bash
ESC_NEUTRAL_US=1600
ESC_NEUTRAL_US_BY_CHANNEL=8:1600,9:1600,10:1600,11:1605
# or per channel:
ESC_NEUTRAL_US_CH11=1605
```

### PCA re-probe

```bash
PCA_REPROBE_S=5   # background retry until PCA9685 @ 0x60 appears (kill-switch-before-agent safe)
```

### Power / safety telemetry

```bash
INA226_ENABLED=1
INA226_ADDRESSES=0x40,0x41,0x44,0x45
LEAK_GPIO=23    # 0 = disabled; HIGH = leak
KILL_GPIO=18    # existing active-low kill sense
```

`/state` and `/health` expose `safety.killSwitchEngaged`, `safety.leakDetected`, thruster `current_a` when INA226 present.

### MAS registry (bench)

```bash
PSATHYRELLA_REGISTRY_KEEPALIVE=1          # default on — heartbeat every 45s when Jetson up
PSATHYRELLA_BENCH_REGISTRY_PERSIST=1      # default on — psathyrella ids never TTL-expire
PSATHYRELLA_REGISTRY_HEARTBEAT_S=45
```

---

## Verification

```powershell
# MAS forward (dry-run cal — no motor motion)
$body = @{ target="side_b"; cmd="nav.esc_calibrate"; params=@{ dry_run=$true } } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://192.168.0.188:8001/api/psathyrella/psathyrella-1/command" -Body $body -ContentType "application/json"

# Jetson state (safety + esc neutral map)
Invoke-RestMethod http://192.168.0.123:8788/state

# Registry (psathyrella-1 should remain after bench idle)
Invoke-RestMethod http://192.168.0.188:8001/api/devices/network
```

**Tests:** `pytest tests/core/test_psathyrella_p1_jul07.py tests/core/test_psathyrella_command.py tests/core/test_psathyrella_forwarding.py -q` → 23 passed.

---

## Deploy

```powershell
cd MAS/mycosoft-mas
git push origin chore/license-notice-readme-sweep-jun25-2026
python scripts/_deploy_psathyrella_mas_7536.py   # update COMMIT hash first
python scripts/_sync_jetson_propulsion_agent.py
```

---

## Install-day checklist (unchanged + new)

1. Power kill switch → PCA V+ / VCC → confirm `:8788/health` shows `pwm:pca9685` (re-probe handles late power).
2. Bench → **Set 0°** per pod (Claude UI or `nav.az_zero`).
3. Optional: `nav.esc_calibrate` with props off after DD ESC install.
4. Trim per-ESC neutral via env if unit 4 drifts.

---

## Lessons learned

- PCA one-shot-at-boot was a foot-gun with 5V VCC after kill switch; background re-probe removes ordering dependency.
- Registry TTL expiry made bench contact look “dark”; immortal psathyrella ids + keepalive fixes GCS contact state without fake RF.
