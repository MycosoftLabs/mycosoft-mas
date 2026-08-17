# Buoy ESC Arming 1600 — Aug 17, 2026

**Date:** Monday Aug 17, 2026  
**Status:** Complete (park + on-disk config; agent **not** restarted)  
**Related:** `docs/BUOY_LIVE_DEMO_READINESS_AUG17_2026.md`  
**Hardware:** Jetson `192.168.0.123`, PCA9685 `0x60` on `i2c-7`, ESC CH8–11

---

## Why

Claude bench-measured Aug 17: **all four ESCs stop at 1600 µs**. Config had `esc_arming_us: 1500` written to CH8–11 on every propulsion-agent start / Jetson reboot. **1500 is ~100 µs into reverse** on this 5V-clock PCA.

## Done this pass (no reboot, no agent restart)

| Item | Result |
|---|---|
| **Parked 1600** | **Y** — `POST :8788/command` `nav.pwm_raw` CH8–11 = 1600; `last_write_ok=true`; `channels_us` 8–11 = 1600.0 |
| **Agent restarted** | **N** — `psathyrella-agent` stayed `active`, MainPID **1895** |
| **Jetson rebooted** | **N** |
| **`esc_arming_us` on disk** | **Y — 1600** (systemd drop-in + `jetson_agent.py` default) |
| **Running process `/state`** | Still reports `esc_arming_us=1500` until the **next** start (in-memory env) |

## Config files changed

| Path | Change |
|---|---|
| Jetson `~/.config/systemd/user/psathyrella-agent.service.d/esc-arming-split.conf` | `ESC_ARMING_US=1500` → **`1600`** (backup `esc-arming-split.conf.bak-esc1600-20260817T085951Z`) |
| Jetson `/home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py` | default `ESC_ARMING_US` **1500 → 1600** (backup `jetson_agent.py.bak-esc1600-20260817T085951Z`) |
| Local `Devices/psathyrella-jetson/jetson_agent.py` | Synced from patched Jetson file |
| Local `Devices/psathyrella-jetson/psathyrella-agent.service.d/esc-arming-split.conf` | `ESC_ARMING_US=1600` |
| MAS `tools/jetson/psathyrella-agent/` | Tracked copies of the patched agent + drop-in |

`systemctl --user daemon-reload` was run so the **next** start loads `ESC_ARMING_US=1600`. The running unit Environment now shows 1600; the live process does not until restart.

## Next start

When Morgan’s kill switch is off **or** he says restart: `systemctl --user restart psathyrella-agent` (do **not** do this tonight). That start will park CH8–11 at **1600**, not 1500.

## `DEADMAN_S`

Live `:8788/health` and unit env: **`DEADMAN_S=0`** (off). Drop-ins `deadman-bench.conf` + `zz-deadman-off.conf` already exist. Repo unit file still lists `DEADMAN_S=15`. **Not enabled tonight** — one-line env already exists; leave it off until water ops.

## Return card

| Question | Answer |
|---|---|
| Parked 1600 | **Y** |
| `esc_arming_us` now 1600 (on disk / next start) | **Y** |
| `esc_arming_us` in running `/state` | **N** (still 1500 until restart) |
| Did you restart the agent | **N** |
