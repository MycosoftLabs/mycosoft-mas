# C-Suite OpenClaw VM Rollout — Complete

**Date**: March 7, 2026  
**Status**: Complete  
**Related plan**: `.cursor/plans/c-suite_vm_rollout_c831a6c2.plan.md`

## Overview

The C-Suite OpenClaw VM Rollout plan is implemented. Four dedicated executive-assistant VMs (CEO, CFO, CTO, COO) are provisioned on the Proxmox host at `192.168.0.202:8006` (co-located with MYCA workspace 191), with role-based provisioning, golden image bootstrap, OpenClaw install, per-role manifests, clone workflow (CEO → CTO → CFO → COO), and MAS/MYCA integration.

## Deliverables Summary

### 1. Proxmox 202 and guest OS

| Item | Path | Description |
|------|------|-------------|
| Proxmox 202 config | `config/proxmox202_csuite.yaml` | Host 192.168.0.202:8006, VMs 192–195, guest_os: windows (next to MYCA 191) |
| Feasibility script | `scripts/validate_proxmox90_feasibility.py` | Validates Proxmox connectivity and sets guest OS (Windows) |

**Guest OS decision:** Windows — macOS not feasible on standard Proxmox; unified Windows path for all four VMs.

### 2. Role-based provisioning

| Item | Path | Description |
|------|------|-------------|
| Provision base | `infra/csuite/provision_base.py` | Credentials, Proxmox API, port helpers |
| Provision C-Suite | `infra/csuite/provision_csuite.py` | Role config, VM spec, create_windows_vm |
| CLI | `scripts/provision_csuite_vm.py` | `--role ceo|cfo|cto|coo|all` with `--dry-run` |

### 3. Golden image bootstrap

| Item | Path | Description |
|------|------|-------------|
| Bootstrap script | `infra/csuite/bootstrap_openclaw_windows.ps1` | Node 22+, OpenClaw, Playwright, C-Suite dirs, persona seeds, env vars |
| Policy defaults | `config/csuite_openclaw_defaults.yaml` | Bounded autonomy, security, reporting endpoints |
| Golden image doc | `docs/CSUITE_OPENCLAW_GOLDEN_IMAGE_MAR07_2026.md` | Full bootstrap and image procedure |

### 4. Role manifests

| Item | Path | Description |
|------|------|-------------|
| Role manifests | `config/csuite_role_manifests.yaml` | CEO (Atlas/MYCAOS), CFO (Meridian/Perplexity), CTO (Forge/Cursor), COO (Nexus/Claude Cowork) |
| Apply manifest | `infra/csuite/apply_role_manifest.ps1` | Installs role-specific apps via winget |

### 5. MAS/MYCA integration

| Item | Path | Description |
|------|------|-------------|
| C-Suite API | `mycosoft_mas/core/routers/csuite_api.py` | Heartbeat, report, escalate, list assistants, health |
| Heartbeat script | `infra/csuite/csuite_heartbeat.ps1` | Scheduled task on each VM; POSTs to MAS 188:8001 |

**Endpoints (MAS 192.168.0.188:8001):**

- `POST /api/csuite/heartbeat` — VM heartbeat (role, ip, status, assistant_name)
- `POST /api/csuite/report` — Task completion, executive summary, operating report
- `POST /api/csuite/escalate` — Escalation when Morgan’s decision needed
- `GET /api/csuite/assistants` — List registered assistants (MYCA/MAS UI)
- `GET /api/csuite/health` — Health check

### 6. VM design

| Role | VM IP | Assistant | Primary tool |
|------|-------|-----------|--------------|
| CEO | 192.168.0.192 | Atlas | MYCAOS |
| CFO | 192.168.0.193 | Meridian | Perplexity |
| CTO | 192.168.0.194 | Forge | Cursor |
| COO | 192.168.0.195 | Nexus | Claude Cowork |

## Architecture

```
Morgan
  ↓
Proxmox 202 (192.168.0.202:8006) — same host as MYCA 191
  ├── CEO VM (192) → Atlas (OpenClaw + MYCAOS)  [from Windows 11 template]
  ├── CTO VM (194) → Forge (OpenClaw + Cursor)  [clone of CEO]
  ├── CFO VM (193) → Meridian (OpenClaw + Perplexity)  [clone of CTO]
  └── COO VM (195) → Nexus (OpenClaw + Claude Cowork)  [clone of CFO]
        ↓ heartbeat / report / escalate
MAS (192.168.0.188:8001) ← C-Suite API
  ↑
MYCA (192.168.0.191) — queries MAS for C-Suite status
```

## Current Blocker: Proxmox 202 Credentials

The rollout script authenticates to Proxmox 202 (192.168.0.202). If Proxmox 202 uses a different root password than the general VM password:

1. Add to `.credentials.local` (or `.env`):  
   `PROXMOX202_PASSWORD=<Proxmox 202 root password>`
2. If Proxmox 202 shares the same password as other VMs, ensure `VM_PASSWORD` or `PROXMOX_PASSWORD` is set and correct.

Once credentials are set, run:
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/run_csuite_full_rollout.py --dry-run   # validate only
python scripts/run_csuite_full_rollout.py             # full rollout
python scripts/run_csuite_full_rollout.py --skip-bootstrap   # provision VMs only, no WinRM bootstrap
```

## Verification

1. **Proxmox 202:** `python scripts/run_csuite_full_rollout.py --dry-run` (validates host and resources)
2. **Provision (dry-run):** `python scripts/provision_csuite_vm.py --role ceo --dry-run`
3. **Bootstrap:** On a Windows VM, run `.\bootstrap_openclaw_windows.ps1 -Role ceo`
4. **Role manifest:** `.\apply_role_manifest.ps1 -Role ceo`
5. **Heartbeat:** `.\csuite_heartbeat.ps1 -Once` (requires CSUITE_ROLE and MAS_API_URL)
6. **MAS C-Suite API:** `curl http://192.168.0.188:8001/api/csuite/health`
7. **List assistants:** `curl http://192.168.0.188:8001/api/csuite/assistants`

## Environment variables (C-Suite VMs)

| Variable | Purpose |
|----------|---------|
| `CSUITE_ROLE` | ceo \| cfo \| cto \| coo |
| `MAS_API_URL` | http://192.168.0.188:8001 |
| `CSUITE_ROOT` | %LOCALAPPDATA%\Mycosoft\C-Suite |
| `OPENCLAW_HOME` | %LOCALAPPDATA%\OpenClaw |

## Known gaps / follow-up

- Escalation forwarding to MYCA task queue or Discord/Slack (TODO in csuite_api.py)
- Redis-backed assistant registry for TTL/stale detection across restarts
- Actual Proxmox 202 VM creation (requires Proxmox host access and Windows 11 template on 202; CEO first, then clone to CTO/CFO/COO)

## Related documents

- `docs/CSUITE_OPENCLAW_GOLDEN_IMAGE_MAR07_2026.md` — Golden image procedure
- `docs/MYCA_DESKTOP_WORKSTATION_COMPLETE_MAR03_2026.md` — VM 191 desktop reference
- `docs/MYCA_OPENWORK_INTEGRATION_MAR05_2026.md` — OpenWork/OpenClaw integration
- `docs/PROXMOX_CREP_RESTORE_MAR05_2026.md` — Proxmox reference
- `config/proxmox202_csuite.yaml` — C-Suite Proxmox config (202, clone workflow)
- `config/csuite_role_manifests.yaml` — Role app manifests
