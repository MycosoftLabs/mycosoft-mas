# CTO VM 194 — Authoritative Source of Truth

**Date**: March 8, 2026  
**Status**: Canonical  
**Supersedes**: All prior CTO/Forge VM specs; Proxmox 90 references (retired)

## Overview

This document is the **single source of truth** for CTO VM 194 (Forge). All provisioning, bootstrap, runtime, and validation flows must align with this spec. Older references to Proxmox 90 or conflicting VM topologies are **retired**.

## Canonical References

| Document | Purpose |
|----------|---------|
| `config/proxmox202_csuite.yaml` | VM topology, VMID, IP, clone chain |
| `docs/CSUITE_OPENCLAW_VM_ROLLOUT_COMPLETE_MAR07_2026.md` | Rollout architecture, MAS integration |
| `docs/PROXMOX202_AUTH_SETUP_MAR08_2026.md` | Proxmox 202 credentials, auth fallback |
| `config/csuite_role_manifests.yaml` | Forge role, apps, persona |
| `config/csuite_openclaw_defaults.yaml` | Bounded autonomy, reporting endpoints |

## CTO VM 194 — Technical Spec

| Property | Value |
|----------|-------|
| **VMID** | 194 |
| **IP** | 192.168.0.194 |
| **Name** | csuite-cto |
| **Role** | CTO |
| **Assistant** | Forge |
| **Primary Tool** | Cursor |
| **Host** | Proxmox 202 (192.168.0.202:8006) |
| **Guest OS** | Windows 11 |

### Current Clone Chain (To Be Replaced)

Per `proxmox202_csuite.yaml`, CTO currently clones from CEO (VMID 192). The CTO Blueprint plans to replace this with a neutral Windows + OpenClaw base image; until then, the clone chain remains CEO → CTO.

### Hardware Spec

| Resource | Value |
|----------|-------|
| Cores | 4 |
| Memory | 16 GB |
| Disk | 128 GB |

## Forge Role Definition

From `csuite_role_manifests.yaml`:

| Property | Value |
|----------|-------|
| **Assistant Name** | Forge |
| **Primary Tool** | Cursor |
| **Proxmox Token Env** | PROXMOX202_CTO_TOKEN |

### Required Apps

- Cursor (winget: Cursor.Cursor)
- Git (winget: Git.Git)
- VS Code (winget: Microsoft.VisualCode)
- GitHub CLI (winget: GitHub.cli)

### Persona

- **Focus**: Coding, code review, architecture, deploy review, issue triage.
- **Skills**: Code review, Architecture documentation, Deploy verification.

### Shared Base (from role manifests)

- Google Chrome, Discord, Slack (all roles)
- Context: Executive assistant for Mycosoft; subordinate to MYCA/MAS. Bounded autonomy.

## MAS Integration

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Heartbeat | `http://192.168.0.188:8001/api/csuite/heartbeat` | VM/Forge status, every 60s |
| Report | `http://192.168.0.188:8001/api/csuite/report` | Task completion, operating report |
| Escalate | `http://192.168.0.188:8001/api/csuite/escalate` | Engineering/security decisions to Morgan |

## CTO Acceptance Contract

The following criteria define success for CTO VM 194. All must hold before declaring the CTO workstation ready:

1. **VM 194 boots cleanly** — Provisioned on Proxmox 202, Windows 11, network reachable at 192.168.0.194.
2. **OpenClaw can drive Cursor and browser surfaces** — OpenClaw installed, Playwright available, can control Cursor and Chrome for autonomous coding tasks.
3. **Forge can receive delegated CTO work from MYCA/Morgan** — MAS or MYCA can push task directives to Forge; Forge has an intake path (Forge bridge/adapter).
4. **Forge can report, escalate, recover, and resume autonomously** — Heartbeat, report, and escalate endpoints used; scheduled tasks and watchdogs keep Forge running 24/7; recovery from crashes/reboots.

## Retired / Conflicting Assumptions

- **Proxmox 90** — All C-Suite VMs run on **Proxmox 202** (192.168.0.202:8006). Proxmox 90 references in older docs are obsolete.
- **Different VMIDs or IPs** — CTO is VMID 194 at 192.168.0.194 only.
- **Manual-only operation** — CTO VM 194 is designed for autonomous 24/7 operation under MYCA/Morgan supervision.

## Next Steps (Blueprint Implementation)

- [ ] Replace CEO→CTO clone with neutral base image (todo: design-clean-image-path)
- [ ] Build Forge runtime adapter/bridge (todo: spec-forge-bridge)
- [ ] Extend guest bootstrap for Cursor workspace sync (todo: extend-guest-bootstrap)
- [ ] Add CTO watchdogs and scheduled tasks (todo: design-ctovm-watchdogs)
- [ ] Harden csuite_api persistence and escalation (todo: close-mas-control-plane-gaps)

## Related

- `docs/CTO_VM_BLUEPRINT_MAR08_2026.md` — Full CTO Blueprint (when created)
- `config/proxmox202_csuite.yaml` — C-Suite topology
- `config/csuite_role_manifests.yaml` — Forge role manifest
