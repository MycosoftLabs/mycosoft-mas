# Firmware Flash Alignment — May 27, 2026

**Date:** May 27, 2026  
**Status:** Ready for physical flash (audit complete)  
**Related:** `docs/FIRMWARE_AUDIT_MAY27_2026.md`, Field Device Console plan

> **OTA / auto‑flash plan (May 29, 2026):** End‑to‑end "flash any board from an orchestrator command" architecture, per‑host topology, artifact pipeline, OpenClaw flash contract, MAS API, safety, and a Phase 0→4 roadmap are in **`docs/MYCOBRAIN_OTA_FIRMWARE_PLAN_MAY29_2026.md`**. The bench/Jetson methods below remain the manual fallback until that roadmap lands.
>
> **Per-board blockers + live probes (May 29, 2026):** Morgan-facing analysis for COM4 (241), Mushroom 1 (123), and Hyphae 1 (228) — what works, exact auto-flash blockers, esptool host, serial port, OpenClaw URL — is in **`docs/MYCOBRAIN_OTA_FLASH_BLOCKERS_MAY29_2026.md`**. Phase 0 COM4 flash code is in-repo; MAS deploy to 188 and first signed artifact still pending.

## Findings

Field Jetson boards (Mushroom 1 @ 123, Hyphae 1 @ 228) report **`recovery-operator-bsec2-v0.7`**, not canonical **`side-a-mdp-2.1.0`**. Console MDP widgets (buzzer presets, NeoPixel patterns, I2C scan) require MDP Side A 2.1.0+.

Local dev PC: **COM4** registered on MAS as `mycobrain-COM4` (May 29) after fixing missing `pyserial` in the MycoBrain service venv. Firmware still **unknown** until probed/flashed; **COM7** remains alternate allowlisted port.

## Target builds

| Device | Side A env | Side B |
|--------|------------|--------|
| Mushroom 1 | `MycoBrain_SideA_MDP` → `mushroom1` | `MycoBrain_SideB_MDP` |
| Hyphae 1 | `MycoBrain_SideA_MDP` → `hyphae1` | `MycoBrain_SideB_MDP` |
| Bench serial | Match device role env | Side B if dual-board |

## Flash methods

### Bench (Windows USB)

From `mycobrain/` repo:

```powershell
.\scripts\flash-mycobrain-production.ps1 -SideAEnv mushroom1   # or hyphae1
```

### Jetson (USB to Side A/B on field unit)

SSH to Jetson, PlatformIO upload from checked-out `mycobrain` firmware tree. See `mycobrain/docs/JETSON_MYCOBRAIN_PRODUCTION_DEPLOY_MAR13_2026.md`.

### MAS relay (approval required)

After MAS deploy, company-authenticated console **Device Agent Chat** or:

```http
POST /api/devices/{device_id}/agent/task
{ "message": "Propose flash Side A to side-a-mdp-2.1.0 mushroom1", "task_type": "firmware_update" }
```

OpenClaw on `:18789` must approve destructive flash jobs.

## Post-flash verification

1. Agent `GET /api/status` → telemetry `fw_version` = `side-a-mdp-2.1.0`
2. MAS registry `firmware_version` updated on next heartbeat
3. `/natureos/mycobrain?device={registry_id}` — rainbow, beep, LED off, I2C scan
4. `GET /api/devices/firmware-audit` → tier **compatible**

## Execution status

| Device | Flashed | Verified |
|--------|---------|----------|
| Mushroom 1 | Pending (requires Jetson USB session) | — |
| Hyphae 1 | Pending | — |
| Local COM4/COM7 | Pending (COM4 online on MAS; flash after build ID) | Heartbeat OK |

Physical flash requires lab access; UI/routing/audit/relay ship in this release regardless.
