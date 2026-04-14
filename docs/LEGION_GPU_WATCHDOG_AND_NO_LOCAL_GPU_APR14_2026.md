# Legion GPU watchdog and no-local-GPU policy — Apr 14, 2026

**Date:** April 14, 2026  
**Status:** Operational guidance  
**Related:** [.cursor/rules/dev-machine-no-local-gpu-inference.mdc](../.cursor/rules/dev-machine-no-local-gpu-inference.mdc)

## Goals

1. **4080A (Earth-2 Legion, 192.168.0.249)** runs earth2studio / Earth-2 API (`8220`, WSL portproxy as documented).
2. **4080B (Voice Legion, 192.168.0.241)** runs Moshi, PersonaPlex bridge, Ollama/Nemotron (`8998`, `8999`, `11434`).
3. **Developer PC** runs Next.js (`3010`) and lightweight tools only — not heavy GPU stacks when Cursor/Claude start “the dev server.”
4. **Recovery** uses **scheduled**, modest-frequency checks on each Legion — not tight loops or constant scripts from the dev machine.

## On each Legion (Windows)

1. **Logon bootstrap (optional):**  
   `Register-MycosoftLegionStartup.ps1 -Role Voice` or `-Role Earth2`  
   Starts the 24x7 stack after login (delayed).

2. **Periodic watchdog (recommended):**  
   As Administrator once:
   ```powershell
   cd <mycosoft-mas>\scripts\gpu-node\windows
   .\Register-LegionGPUWatchdog.ps1 -Role Voice -IntervalMinutes 15
   # or
   .\Register-LegionGPUWatchdog.ps1 -Role Earth2 -IntervalMinutes 15
   ```
   `Invoke-LegionGPUWatchdog.ps1` GETs `http://127.0.0.1:8999/health` (Voice) or `http://127.0.0.1:8220/health` (Earth-2). After **three** consecutive failures it invokes the matching `Start-Legion*24x7.ps1` (idempotent).

3. **Unregister:**  
   `.\Register-LegionGPUWatchdog.ps1 -Role Voice -Unregister`

## Why not GitHub Actions on a schedule for LAN health?

GitHub-hosted runners **cannot** reach `192.168.0.x`. Use:

- Watchdog tasks **on the Legions** (above), and/or  
- A **self-hosted runner** on the LAN (optional), and/or  
- `scripts/verify_cross_system_health.ps1` from a PC on the same UniFi LAN when debugging.

## Website dev machine

Set bridge URL to the Voice Legion, not localhost:

- `PERSONAPLEX_BRIDGE_URL=http://192.168.0.241:8999`
- Do **not** enable `NEXT_PUBLIC_USE_LOCAL_GPU` / `USE_LOCAL_VOICE` for routine work.
