# C-Suite Neutral Base Image Strategy

**Date**: March 8, 2026  
**Status**: Design Complete  
**Supersedes**: CEO→CTO→CFO→COO clone chain (role contamination risk)

## Overview

Replace the risky **CEO → CTO → CFO → COO** clone chain with a **neutral Windows 11 + OpenClaw base template**. All C-Suite roles (CEO, CTO, CFO, COO) derive from the same clean base, then apply role-specific overlays. No role inherits another role's state, preventing contamination.

## Problem with Current Chain

| Risk | Description |
|------|-------------|
| Role contamination | CTO inherits CEO (Atlas/MYCAOS) state; CFO inherits CTO (Forge/Cursor) state |
| Stale credentials | Tokens, cookies, or session data from previous role may persist |
| App conflicts | Multiple primary tools (MYCAOS + Cursor + Perplexity) can conflict |
| Debugging opacity | Hard to isolate issues to a specific role when state is chained |

## Target Architecture

```
Neutral Base Template (VMID 9100 or configurable)
├── Windows 11
├── bootstrap_openclaw_windows.ps1 -BaseOnly (Node, OpenClaw, Playwright, C-Suite dirs)
├── Shared apps only (Chrome, Discord, Slack) — optional in base or first-boot
└── NO role-specific apps (Cursor, Perplexity, Claude Cowork, MYCAOS)

After clone for each role:
└── apply_role_manifest.ps1 -Role {ceo|cto|cfo|coo}
```

## Design Decisions

### 1. Base-Only Bootstrap Flag

Extend `bootstrap_openclaw_windows.ps1` with `-BaseOnly`:

- Skips role-specific persona seeds (or uses a generic seed)
- Installs Node, OpenClaw, Playwright, C-Suite directories
- Sets MAS_API_URL, CSUITE_ROOT, OPENCLAW_HOME
- Does **not** run `apply_role_manifest.ps1`

### 2. Base Template VMID

Add to `config/proxmox202_csuite.yaml`:

```yaml
build_source:
  # Neutral base: Windows 11 + OpenClaw + shared tooling (no role apps)
  base_template_vmid: 9100   # C-Suite neutral base; create once, reuse
  template_vmid: null       # Legacy: CEO-specific template (deprecated)
  iso_path: "local:iso/Win11_24H2_English_x64.iso"
  create_blank: true
```

### 3. Clone Source Logic

| Role | When base_template_vmid set | When template_vmid set (legacy) |
|------|----------------------------|----------------------------------|
| CEO | Clone from base 9100 | Clone from template |
| CTO | Clone from base 9100 | Clone from CEO (192) |
| CFO | Clone from base 9100 | Clone from CTO (194) |
| COO | Clone from base 9100 | Clone from CFO (193) |

When `base_template_vmid` is set, **all** roles clone from it. When only `template_vmid` is set, CEO uses template and others use clone chain.

### 4. Role Overlay (Unchanged)

After clone, guest bootstrap runs:

1. `bootstrap_openclaw_windows.ps1 -Role {role} -SkipOpenClawInstall` (refresh config, persona)
2. `apply_role_manifest.ps1 -Role {role}` (install Cursor, Perplexity, etc.)

## Implementation Phases

### Phase 1: Config and Provision Logic (This Blueprint)

- Add `base_template_vmid` to `proxmox202_csuite.yaml`
- Update `provision_csuite.py` to prefer `base_template_vmid` over `clone_from` when set
- Document the golden base creation procedure

### Phase 2: Bootstrap -BaseOnly

- Add `-BaseOnly` to `bootstrap_openclaw_windows.ps1`
- Create one-time procedure to build neutral base VM and convert to template 9100

### Phase 3: Rollout Migration

- Create neutral base template (manual or automated)
- Set `base_template_vmid: 9100` in config
- Re-provision CTO, CFO, COO from base (existing VMs can be destroyed and recreated)

## Config Changes (proxmox202_csuite.yaml)

```yaml
build_source:
  base_template_vmid: 9100   # Neutral C-Suite base (Windows + OpenClaw, no role apps)
  template_vmid: null       # Fallback when base not yet built
  iso_path: "local:iso/Win11_24H2_English_x64.iso"
  create_blank: true
```

## Provision Logic Update (provision_csuite.py)

```python
# Pseudocode
base_vmid = build_source.get("base_template_vmid")
if base_vmid and pve_has_vm(base_vmid):
    # All roles clone from neutral base
    clone_from = base_vmid
else:
    # Legacy: use clone_from from role config (CEO→CTO→CFO→COO)
    clone_from = role_cfg.get("clone_from")
```

## Golden Base Creation Procedure

1. Create blank Windows 11 VM (or use existing template)
2. Install Windows 11, apply updates, configure WinRM
3. Run `bootstrap_openclaw_windows.ps1 -Role ceo -BaseOnly` (or new -BaseOnly flag)
4. Optionally install shared apps (Chrome, Discord, Slack) via winget
5. Sysprep or generalize for cloning (Windows best practice)
6. Stop VM, convert to template (VMID 9100) in Proxmox
7. Set `base_template_vmid: 9100` in config

## Files to Modify

| File | Change |
|------|--------|
| `config/proxmox202_csuite.yaml` | Add `base_template_vmid` |
| `infra/csuite/provision_csuite.py` | Prefer base template over clone chain |
| `infra/csuite/bootstrap_openclaw_windows.ps1` | Add `-BaseOnly` flag (Phase 2) |

## Related

- `docs/CTO_VM194_AUTHORITATIVE_SPEC_MAR08_2026.md` — CTO spec
- `docs/CSUITE_OPENCLAW_GOLDEN_IMAGE_MAR07_2026.md` — Golden image procedure
- `config/proxmox202_csuite.yaml` — C-Suite config
