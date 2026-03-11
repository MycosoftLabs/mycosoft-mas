# C-Suite Rollout Clone Fixes — Mar 07, 2026

**Status:** Code fixes complete. Rollout blocked on Proxmox 202 auth until credentials added.

## Summary

After Cursor crashed during the C-Suite rollout, the prior run had failed because:
1. **CFO clone** — Task timed out (600s). Cloning 128GB disks can take 15–30+ minutes.
2. **COO clone** — Source VM 193 was locked from the failed CFO clone; unlock timed out.

## Code Changes

### 1. Increased clone timeout (`infra/csuite/provision_csuite.py`)

- Raised `wait_for_pve_task` timeout from **600s** to **1800s** (30 min) for clone operations.
- Prevents premature timeout on large disk clones.

### 2. Unlock before start when VM exists (`infra/csuite/provision_csuite.py`)

- When a VM already exists but is stopped, call `pve_unlock_vm` before `status/start`.
- Handles stale locks from prior failed or timed-out clones on re-run.

### 3. Clearer auth error message (`scripts/run_csuite_full_rollout.py`)

- On HTTP 401, instructs user to add `PROXMOX202_PASSWORD` to `.credentials.local`.

## Current Rollout Block

The rollout returns **HTTP 401** (auth failed) against Proxmox 202. Add to `.credentials.local`:

```
PROXMOX202_PASSWORD=<Proxmox 202 root password>
```

(or `PROXMOX_PASSWORD` if it matches your other Proxmox hosts).

## Re-run After Fixing Auth

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/run_csuite_full_rollout.py --skip-bootstrap
```

With auth fixed, the flow will:
- CEO (192) — already running
- CTO (194) — start existing VM
- CFO (193) — unlock source 194, clone (up to 30 min wait), start
- COO (195) — unlock source 193, clone (up to 30 min wait), start

## Related

- [config/proxmox202_csuite.yaml](../config/proxmox202_csuite.yaml)
- [infra/csuite/provision_csuite.py](../infra/csuite/provision_csuite.py)
- [scripts/run_csuite_full_rollout.py](../scripts/run_csuite_full_rollout.py)
