# COM4 Bench and Hyphae Pi OTA — Local Session Complete — May 29, 2026

**Date:** May 29, 2026  
**Status:** Phase A complete (verified). Phase B infrastructure complete; live Hyphae flash blocked on Pi SSH credentials.  
**Plan:** `COM4 then Hyphae OTA` (local-only; Mushroom 1 protected)  
**Deploy gate:** No push to `main`, no VM 187/188 deploy, no Cloudflare purge in this session.

---

## Executive summary

| Phase | Outcome |
|-------|---------|
| **A — COM4 bench** | Identified BSEC2 → built MDP 2.1.0 standalone → live flash success → Earth Simulator visibility on localhost:3010 |
| **B — Hyphae Pi** | HTTP probe OK (`8787`, `/dev/ttyACM0`); OpenClaw `:18789` down; SSH sidecar + MAS routing implemented; **live flash not executed** (SSH auth failed) |
| **Mushroom 1 (123)** | Untouched — still `recovery-operator-bsec2-v0.7` on `:8787` |

---

## Phase A — COM4 (dev PC 241)

### A1 Pre-flight
- MycoBrain `:8003` healthy
- MAS registry: `mycobrain-COM4` on `192.168.0.241:8003`
- Dev server `:3010` running

### A2 Identify
- **Before flash:** BSEC2 DeviceManager (`mycobrain.sideA.bsec2`)
- Recorded in `docs/FIRMWARE_AUDIT_MAY27_2026.md` (COM4 section)

### A3 Artifacts
- PlatformIO env `standalone` + `hyphae1` in `mycobrain/firmware/MycoBrain_SideA_MDP/`
- Staged under `data/firmware_artifacts/side-a-mdp-2.1.0/`:
  - `side-a-mdp-2.1.0_standalone_merged.bin`
  - `side-a-mdp-2.1.0_hyphae1_merged.bin`
  - `manifest.json`
- Build script: `scripts/build_firmware_artifact.ps1`
- **Gap:** Science-comms (optical/acoustic TX) not merged into MDP build yet — follow-up firmware env

### A4 Fleet visibility (website, plan-approved)
- `lib/devices/dev-bench-location.ts`, Earth Simulator + network API updates
- COM4 appears on `localhost:3010/api/earth-simulator/devices`

### A5 Live flash
- Dry-run + live flash via `scripts/test_com4_flash_dry_run.ps1 -LiveFlash`
- Result: `docs/com4_flash_dry_run_results.json`, state `success`

### A6 Verification
| Check | Result |
|-------|--------|
| MDP firmware | `side-a-mdp-2.1.0`, role `standalone`, MDP v1 |
| Service | COM4 connected on `:8003` |
| Earth Simulator API | `bench-com4` + `mycobrain-COM4` visible |
| Science comms widgets | Not in MDP-only build — documented gap |
| Mushroom 123 | Still `recovery-operator-bsec2-v0.7`, online |

---

## Phase B — Hyphae Pi (228)

### B1 Probe
- HTTP: `http://192.168.0.228:8787/api/status` — OK, `/dev/ttyACM0`, recovery firmware
- OpenClaw `:18789` — unreachable
- SSH port 22 open; password auth failed (see `docs/hyphae_pi_probe_results.json`)

### B2 Implementation (local repo)
- `services/mycobrain/pi_flash_sidecar.py` — esptool on Pi with `APPROVE_FLASH` gate
- `scripts/hyphae_pi_flash.py` — SCP + SSH exec, `--probe-only`, multi-user retry
- `scripts/test_hyphae_flash_dry_run.ps1`
- `mycosoft_mas/core/routers/firmware_flash_api.py` — Hyphae-only routing, explicit **403** for Mushroom 1, OpenClaw then SSH fallback

### B3 / B4 — Blocked
Live and SSH dry-run flash require Pi SSH credentials not present in `.credentials.local` (`HYPHAE_SSH_USER` / `HYPHAE_SSH_PASSWORD` or key). Recovery operator has no HTTP flash route.

**Unblock:** Add Pi SSH creds, then:
```powershell
cd MAS/mycosoft-mas
.\scripts\test_hyphae_flash_dry_run.ps1          # dry-run
$env:APPROVE_FLASH='true'
.\scripts\test_hyphae_flash_dry_run.ps1 -LiveFlash
```

---

## Files touched (execution)

| Area | Paths |
|------|-------|
| Flash executor | `services/mycobrain/flash_executor.py`, `mycobrain_service_standalone.py` |
| Artifacts | `data/firmware_artifacts/side-a-mdp-2.1.0/*` |
| Firmware build | `mycobrain/firmware/MycoBrain_SideA_MDP/` |
| Hyphae OTA | `pi_flash_sidecar.py`, `hyphae_pi_flash.py`, `firmware_flash_api.py` |
| Website fleet | `WEBSITE/website/lib/devices/dev-bench-location.ts`, earth-simulator + network routes |
| Scripts | `build_firmware_artifact.ps1`, `test_com4_flash_dry_run.ps1`, `test_hyphae_flash_dry_run.ps1` |

---

## Next steps (after Morgan approval)

1. Add Hyphae Pi SSH credentials → run B3 dry-run + live flash on 228 only
2. Feature branch PR (MAS + mycobrain + website fleet fix) — **not direct to main**
3. Deploy MAS `firmware_flash_api` to 188; website to 187 if fleet changes kept
4. Mushroom 1 flash — separate lab window, duplicate proven Hyphae path

---

## Lessons learned

- Profile-scoped artifact glob prevents flashing wrong binary (hyphae vs standalone)
- Port release + watcher pause required before esptool on COM4
- Pi field hosts may not share VM SSH password — use dedicated `HYPHAE_SSH_*` env vars
- HTTP recovery operator sufficient for health probe when SSH unavailable
