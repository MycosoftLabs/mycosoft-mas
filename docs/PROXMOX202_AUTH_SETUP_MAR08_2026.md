# Proxmox 202 Authentication Setup

**Date**: March 8, 2026
**Status**: Complete
**Target**: Proxmox 192.168.0.202:8006, node `pve` — C-Suite VM rollout

## Overview

Proxmox 202 (`root@192.168.0.202`) uses credentials that may **differ** from guest VMs (187–191). Per `vm-credentials.mdc`: guest VMs use `VM_PASSWORD`; Proxmox root may use a different password. The C-Suite rollout needs valid Proxmox 202 auth for API or SSH fallback.

## One-Time Setup (choose one)

### Option A: Password (recommended for quick setup)

1. Add to `MAS/mycosoft-mas/.credentials.local`:
   ```
   PROXMOX202_PASSWORD=<actual Proxmox 202 root password>
   ```
2. Ensure the file is in `.gitignore` (it should be).
3. Run: `python scripts/run_csuite_full_rollout.py`

### Option B: API Token

1. In Proxmox web UI (https://192.168.0.202:8006): Datacenter → Permissions → API Tokens → Add
2. Create token for `root@pam` with appropriate privileges (VM.Allocate, VM.Config, etc.)
3. Add to `.credentials.local`:
   ```
   PROXMOX202_TOKEN=root@pam!csuite=<token-secret>
   ```
   Or use `PVEAPIToken=...` format if your token includes the prefix.
4. Run rollout.

### Option C: SSH Key (passwordless, best for automation)

1. Generate keypair (if needed):
   ```
   ssh-keygen -t ed25519 -f config/proxmox202_id_rsa -N ""
   ```
2. Add public key to Proxmox 202 root:
   - SSH to Proxmox console or use web shell
   - `mkdir -p /root/.ssh && echo "ssh-ed25519 AAAA..." >> /root/.ssh/authorized_keys`
   - Or: `ssh-copy-id -i config/proxmox202_id_rsa.pub root@192.168.0.202`
3. Ensure private key exists at `config/proxmox202_id_rsa` or set:
   ```
   PROXMOX202_SSH_KEY=C:\path\to\private_key
   ```
4. Run rollout.

## Credential Fallback Chain

| Priority | Source | Used when |
|----------|--------|-----------|
| 1 | `PROXMOX202_PASSWORD` | Password auth (API ticket or SSH) |
| 2 | `PROXMOX_PASSWORD` | If PROXMOX202 not set |
| 3 | `VM_PASSWORD` | Last fallback (guest VM password) |

**Note**: If Proxmox 202 root uses a different password than guest VMs, `VM_PASSWORD` will fail. You must set `PROXMOX202_PASSWORD` explicitly.

## Scripts

- `scripts/ensure_proxmox202_credentials.py` — Ensures PROXMOX202_PASSWORD in `.credentials.local`; if missing, copies from PROXMOX_PASSWORD or VM_PASSWORD. Run automatically by rollout.
- `scripts/run_csuite_full_rollout.py` — Full C-Suite rollout (CEO, CTO, CFO, COO).

## Auth Attempt Order

1. **Proxmox API** (token or ticket from password)
2. **SSH fallback** (when API returns 401):
   - PROXMOX202_SSH_KEY / config/proxmox202_id_rsa
   - Password (paramiko)
   - ~/.ssh/id_ed25519, ~/.ssh/id_rsa
   - plink (Windows) or sshpass (Linux)

## Related

- `config/proxmox202_csuite.yaml` — C-Suite VM spec
- `docs/CSUITE_ROLLOUT_CLONE_FIXES_MAR07_2026.md` — Clone fixes
- `infra/csuite/provision_ssh.py` — SSH fallback implementation
