# C-Suite OpenClaw Golden Image — Bootstrap Complete

**Date**: March 7, 2026  
**Status**: Complete  
**Related plan**: `.cursor/plans/c-suite_vm_rollout_c831a6c2.plan.md`

## Overview

The golden desktop bootstrap for C-Suite executive assistant VMs (CEO, CFO, CTO, COO) is implemented. Each Windows VM runs OpenClaw as the personal assistant shell, with browser automation prerequisites, remote access hints, persona seeds, and shared policy defaults.

## Bootstrap Layers

| Layer | Components |
|-------|------------|
| **1. Directories** | `%LOCALAPPDATA%\Mycosoft\C-Suite\memory`, `skills`, `logs`, `role_prompts`, `persona_seeds` |
| **2. Node.js** | Node 22+ via `winget install OpenJS.NodeJS.LTS` |
| **3. OpenClaw** | `iwr -useb https://openclaw.ai/install.ps1 \| iex` with `-NoOnboard` for automation |
| **4. Browser automation** | Playwright Chromium via `npx playwright install chromium` |
| **5. Persona seeds** | Per-role stub in `persona_seeds\{role}_default.md` |
| **6. Policy defaults** | `config/csuite_openclaw_defaults.yaml` (bounded autonomy, security, reporting) |

## Files

| File | Purpose |
|------|---------|
| `infra/csuite/bootstrap_openclaw_windows.ps1` | Golden image bootstrap — run after Windows install |
| `config/csuite_openclaw_defaults.yaml` | Shared policy defaults (bounded autonomy, security, reporting) |

## Usage

Run on a fresh Windows VM (after OS install via Proxmox console):

```powershell
# From repo or copied script
.\infra\csuite\bootstrap_openclaw_windows.ps1 -Role ceo

# Skip OpenClaw reinstall when re-running
.\infra\csuite\bootstrap_openclaw_windows.ps1 -Role cfo -SkipOpenClawInstall
```

Roles: `ceo`, `cfo`, `cto`, `coo`.

## Environment Variables Set

| Variable | Value |
|----------|-------|
| `OPENCLAW_HOME` | `%LOCALAPPDATA%\OpenClaw` |
| `OPENCLAW_STATE_DIR` | `%LOCALAPPDATA%\OpenClaw\state` |
| `CSUITE_ROOT` | `%LOCALAPPDATA%\Mycosoft\C-Suite` |

## Next Steps

- **Role manifests** (Todo 4): Per-role app stacks (MYCAOS, Perplexity, Cursor, Claude Cowork)
- **MYCA/MAS integration** (Todo 5): Heartbeat, reporting, escalation wiring

## Related Documents

- [C-Suite Plan](.cursor/plans/c-suite_vm_rollout_c831a6c2.plan.md)
- [MYCA Desktop Workstation](./MYCA_DESKTOP_WORKSTATION_COMPLETE_MAR03_2026.md) — VM 191 Linux desktop reference
- [MYCA OpenWork Integration](./MYCA_OPENWORK_INTEGRATION_MAR05_2026.md) — OpenWork/OpenClaw patterns
