# CTO VM 194 — Rollout Verification Checklist

**Date:** March 8, 2026  
**Status:** Acceptance Checklist (Pre-Implementation)  
**Related:** CTO VM Blueprint, `docs/CTO_VM194_AUTHORITATIVE_SPEC_MAR08_2026.md`, `docs/CSUITE_NEUTRAL_BASE_IMAGE_STRATEGY_MAR08_2026.md`

---

## Purpose

This checklist defines acceptance criteria for the CTO VM 194 rollout **before implementation begins**. All items must pass before the CTO VM is considered production-ready.

---

## 1. Proxmox 202 and Template Readiness

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 1.1 | Proxmox 202 auth works (API token or password) | `scripts/discover_proxmox202_windows.py` or manual `curl -k https://192.168.0.202:8006/api2/json/version` with auth | ☐ |
| 1.2 | Windows 11 template exists and is usable | `config/proxmox202_csuite.yaml` → `base_template_vmid` points to valid template | ☐ |
| 1.3 | Neutral base image (or CEO template) is in place | Per `CSUITE_NEUTRAL_BASE_IMAGE_STRATEGY_MAR08_2026.md`; provisioning clones from correct source | ☐ |

---

## 2. VM 194 Provisioning

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 2.1 | VM 194 can be provisioned from the base path | Run `provision_csuite.py` (or equivalent) with role=cto; VM boots | ☐ |
| 2.2 | VM 194 has correct IP (192.168.0.194) | `ping 192.168.0.194` or guest network config | ☐ |
| 2.3 | Guest OS is Windows 11 | RDP or console; `winver` shows Windows 11 | ☐ |
| 2.4 | Hardware spec: 4 cores, 16 GB RAM, 128 GB disk | Proxmox VM config | ☐ |

---

## 3. Forge Tooling Install

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 3.1 | OpenClaw is installed and runnable | Per `bootstrap_openclaw_windows.ps1`; OpenClaw can start | ☐ |
| 3.2 | Cursor is installed | `winget list Cursor.Cursor` or launch Cursor | ☐ |
| 3.3 | Git is installed | `git --version` | ☐ |
| 3.4 | VS Code is installed | `winget list Microsoft.VisualCode` or launch | ☐ |
| 3.5 | GitHub CLI is installed and auth-ready | `gh auth status` (auth may need manual setup) | ☐ |

---

## 4. Workspace and Rules/Skills Sync

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 4.1 | Workspace is cloned to `$env:CTO_CODE_ROOT` | Repo exists at expected path (e.g. `C:\Users\Administrator\Mycosoft\CODE`) | ☐ |
| 4.2 | Python and Node runtimes are available | `python --version`, `node --version` | ☐ |
| 4.3 | Cursor system sync runs successfully | `python scripts/sync_cursor_system.py` completes without error | ☐ |
| 4.4 | Rules, agents, and skills load cohesively | Open Cursor; verify `.cursor/rules`, `.cursor/agents`, `.cursor/skills` populated | ☐ |
| 4.5 | MAS/MINDEX/MYCA URLs and credentials in env | `.env` or env vars for `MAS_API_URL`, `MINDEX_API_URL`, etc. | ☐ |

---

## 5. Forge Bridge — Heartbeat, Report, Escalate

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 5.1 | Forge adapter can send heartbeat | `python -c "from mycosoft_mas.edge.forge_adapter import ForgeAdapter; import asyncio; asyncio.run(ForgeAdapter().send_heartbeat())"` (from MAS or CTO VM with MAS reachable) | ☐ |
| 5.2 | Forge adapter can send report | `POST /api/csuite/report` with role=CTO, assistant_name=Forge | ☐ |
| 5.3 | Forge adapter can send escalation | `POST /api/csuite/escalate` with CTO/Forge identity | ☐ |
| 5.4 | MAS persists and surfaces CTO data | `GET /api/csuite/forge/dashboard`, `GET /api/csuite/forge/summary` return data | ☐ |
| 5.5 | Escalations visible to Morgan | `GET /api/csuite/escalations` shows CTO escalations when present | ☐ |

---

## 6. Scheduled Tasks and Watchdogs

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 6.1 | Heartbeat task runs every minute | Task exists; check MAS for recent CTO heartbeat | ☐ |
| 6.2 | Forge bridge watchdog restarts bridge if it dies | Kill bridge process; watchdog restarts it within interval | ☐ |
| 6.3 | Cursor system sync task runs periodically | Task exists; rules/agents/skills stay fresh after sync | ☐ |
| 6.4 | OpenClaw health task restarts OpenClaw if needed | Kill OpenClaw; task restarts it | ☐ |
| 6.5 | Operating report task sends periodic summary | MAS receives operating reports from Forge | ☐ |
| 6.6 | Tasks survive reboot | Reboot VM 194; after boot, all tasks run and CTO services recover | ☐ |

---

## 7. MYCA Control Plane Visibility

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 7.1 | MYCA can see Forge health | Morgan/MYCA surface shows Forge status (e.g. via csuite/forge/summary) | ☐ |
| 7.2 | MYCA can see recent CTO work | Report history, task completions visible in dashboard | ☐ |
| 7.3 | Stale CTO tasks are surfaced | `stale_tasks_count` and `stale_tasks` in forge/dashboard when applicable | ☐ |
| 7.4 | Escalations forward to Morgan | Escalations appear in MYCA/Morgan oversight surface | ☐ |

---

## 8. Canonical Spec and Future Rebuilds

| # | Criterion | How to Verify | Pass |
|---|-----------|---------------|------|
| 8.1 | CTO VM 194 design is documented as canonical spec | `docs/CTO_VM194_AUTHORITATIVE_SPEC_MAR08_2026.md` exists and is current | ☐ |
| 8.2 | Bootstrap and watchdog scripts are in repo | `infra/csuite/bootstrap_cto_guest.ps1`, `scripts/install-cto-vm-watchdog.ps1`, etc. | ☐ |
| 8.3 | A fresh clone can be rebuilt from this spec | New VM provisioned from neutral base + CTO role overlay; all checklist items pass | ☐ |

---

## Rollout Readiness

**All sections must pass** before declaring the CTO VM 194 rollout complete. Use this checklist during:

- Initial rollout
- Post-reboot verification
- Fresh-clone rebuilds

---

## References

- `docs/CTO_VM194_AUTHORITATIVE_SPEC_MAR08_2026.md`
- `docs/CSUITE_NEUTRAL_BASE_IMAGE_STRATEGY_MAR08_2026.md`
- `docs/FORGE_BRIDGE_SPEC_MAR08_2026.md`
- `docs/CSUITE_OPERATOR_CONTRACT_MAR08_2026.md`
- `scripts/install-cto-vm-watchdog.ps1`
- `infra/csuite/bootstrap_guest_remote.py`
