# C-Suite COO Provision — Complete (Blocked on Auth) — Mar 07, 2026

**Status:** Code and config complete. Provision blocked on Proxmox 202 authentication.

## Summary

COO VM (195) is fully defined in `config/proxmox202_csuite.yaml` and ready to provision. All automation is in place. Provision fails because Proxmox 202 API credentials lack sufficient privileges.

## COO VM Definition

| Property | Value |
|----------|-------|
| VMID | 195 |
| Name | csuite-coo |
| IP | 192.168.0.195 |
| Role | COO |
| Primary Tool | Claude Cowork |
| Assistant Name | Nexus |
| Clone Source | CFO (VM 193) |

## Auth Failure Modes

| Auth Method | Result | Cause |
|-------------|--------|-------|
| Token (`PROXMOX202_TOKEN` / `PROXMOX_TOKEN`) | HTTP 403 | Token lacks `VM.Clone`, `VM.Config.*` privileges |
| Password (`PROXMOX202_PASSWORD` in `.credentials.local`) | HTTP 401 | Password rejected (wrong, missing, or not root) |

## Code Changes Made

### 1. `PROXMOX202_USE_PASSWORD=1` — Force Password Auth (`infra/csuite/provision_base.py`)

When set, skips API token and uses only root@pam + password. Use when the token has limited privileges.

```powershell
$env:PROXMOX202_USE_PASSWORD="1"
python scripts/provision_csuite_vm.py --role coo
```

### 2. Credential Load Chain (unchanged)

Credentials loaded from:
- `.credentials.local` (MAS repo)
- `config/proxmox202_credentials.env`
- Env vars: `PROXMOX202_PASSWORD`, `PROXMOX_PASSWORD`, `VM_PASSWORD`

## How to Fix Auth and Provision COO

### Option A: Root Password

1. Add to `.credentials.local` (MAS repo root):
   ```
   PROXMOX202_PASSWORD=<Proxmox 202 root password>
   ```
2. If using a limited token, either unset `PROXMOX202_TOKEN` or set:
   ```
   PROXMOX202_USE_PASSWORD=1
   ```
   before running provision.
3. Run:
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   $env:PROXMOX202_USE_PASSWORD="1"  # if token is limited
   python scripts/provision_csuite_vm.py --role coo
   ```

### Option B: Full-Privilege Token

Create an API token on Proxmox 202 with at least:
- `VM.Clone`
- `VM.Config.Disk`, `VM.Config.CDROM`, `VM.Config.CPU`, `VM.Config.Memory`, `VM.Config.Network`, `VM.Config.HWType`, `VM.Config.Options`, `VM.Config.Cloudinit`

Set `PROXMOX202_TOKEN` and run provision (no `PROXMOX202_USE_PASSWORD` needed).

## Provision Commands

```powershell
# Single role (COO only)
python scripts/provision_csuite_vm.py --role coo

# Full C-Suite rollout (any missing VMs in order)
python scripts/run_csuite_full_rollout.py --skip-bootstrap
```

## Prerequisites

- CFO (VM 193) must exist and be running (COO clones from CFO).
- If CFO is locked from a prior failed clone, the rollout script will attempt unlock before clone.
- Clone timeout is 30 min for large disks.

## Verification After Success

1. Proxmox 202 UI: VM 195 `csuite-coo` exists and is running.
2. Guest IP: `192.168.0.195` reachable (after guest networking configured).
3. MAS/website: COO VM visible in device/VM registries if integrated.

## Related Docs

- [CSUITE_ROLLOUT_CLONE_FIXES_MAR07_2026.md](CSUITE_ROLLOUT_CLONE_FIXES_MAR07_2026.md) — Clone timeout, unlock-before-start, auth hint.
- [PROXMOX202_AUTH_SETUP_MAR08_2026.md](PROXMOX202_AUTH_SETUP_MAR08_2026.md) — One-time Proxmox 202 auth setup.
- [config/proxmox202_csuite.yaml](../config/proxmox202_csuite.yaml) — Full C-Suite VM definitions.
