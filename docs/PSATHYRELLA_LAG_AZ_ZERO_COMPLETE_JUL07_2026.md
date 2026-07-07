# Psathyrella Lag Fix + nav.az_zero — Complete

**Date:** Jul 07, 2026  
**Status:** Complete  
**Related:** `CODE/docs/PSATHYRELLA_CURSOR_HANDOFF_JUL07_LAG_AND_AZIMUTH_HOME.md`, `docs/PSATHYRELLA_BACKEND_P0_P6_STATUS_JUN27_2026.md`

---

## Scope

Cursor lane items from Claude's Jul 07 addendum:

1. Persistent HTTP keep-alive in MAS `jetson_forward.py` (fix ~1s TCP lag per command)
2. Commit `nav.az_zero` into tracked `jetson_agent.py`
3. Add `nav.az_zero` to MAS allowlist + command handler; deploy to 188

GCS bench proxy + UI were already built and verified by Claude (out of scope).

---

## Delivered

| Artifact | Path |
|----------|------|
| Keep-alive relay | `mycosoft_mas/devices/psathyrella/jetson_forward.py` |
| MAS command handler | `mycosoft_mas/devices/psathyrella/command_handler.py` |
| Jetson agent | `devices/psathyrella-jetson/jetson_agent.py` |
| Tests | `tests/core/test_psathyrella_command.py`, `tests/core/test_psathyrella_forwarding.py` |
| Jetson sync script | `scripts/_sync_jetson_propulsion_agent.py` |

**Commit:** `7536f553e` on branch `chore/license-notice-readme-sweep-jun25-2026`

---

## Verification

### MAS VM 188

- `GET http://192.168.0.188:8001/health` → `git_sha=7536f553e`, status healthy
- `POST .../command` `{target:"side_b", cmd:"nav.az_zero", params:{}}` → `ok:true`, `ack.state=applied`, `detail: azimuth home set for [0, 1, 2, 3]`

### Latency (keep-alive)

Five consecutive `nav.thrust_vector` commands through MAS:

| # | Round-trip ms |
|---|---------------|
| 1 | 3191 (cold) |
| 2–5 | 13–15 |

Matches Claude's diagnosis: first connection pays TCP setup; reused connection is fast.

### Jetson 123

- `scripts/_sync_jetson_propulsion_agent.py` → agent restarted, `:8788/health` ok

---

## How to re-deploy

```powershell
cd MAS/mycosoft-mas
git push origin chore/license-notice-readme-sweep-jun25-2026
python scripts/_deploy_psathyrella_mas_7536.py   # or reset VM to latest commit + restart mas-orchestrator
python scripts/_sync_jetson_propulsion_agent.py
```

---

## Follow-up (P1, not in this task)

- AS5600 magnetic encoders for closed-loop azimuth
- ESC range calibration + per-ESC neutral trim env
- PCA background re-probe in agent
- Registry heartbeat / bench no-expiry
- INA226 / kill-switch / leak telemetry hooks

---

## Lessons learned

- Module-level `httpx.AsyncClient` with keep-alive collapses MAS→Jetson relay from ~1s to ~15ms for steady joystick use.
- Bench calibration (`nav.az_zero`) can use Claude's direct proxy today; MAS path now supports the same command for standard GCS routing.
