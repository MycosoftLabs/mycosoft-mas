# C-Suite VMs: Windows Install Fix (scsi0 → sata0)

**Date**: March 7, 2026  
**Status**: Complete  
**Related**: `infra/csuite/fix_vm_disk_sata.py`, `config/proxmox202_csuite.yaml`

## Problem

C-Suite VMs (192–195) on Proxmox 202 use **VirtIO SCSI** (`scsi0`) for the system disk. The Windows installer does not include VirtIO SCSI drivers, so:

- **Upgrade option** is grayed out ("Upgrade isn't available")
- **Custom install** shows no disk
- Installation cannot proceed

## Root Cause

VMs were provisioned with `scsi0` (VirtIO SCSI). Windows requires drivers to see VirtIO disks; the installer media does not include them.

## Solution

Switch the system disk from **SCSI** to **SATA**. Windows supports SATA natively and will see the disk.

## How to Fix

Run the migration script from the MAS repo:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

# Dry run (no changes)
python infra/csuite/fix_vm_disk_sata.py --use-ssh --dry-run

# Apply fix to VMs 192, 193, 194, 195
python infra/csuite/fix_vm_disk_sata.py --use-ssh
```

### Options

| Option | Description |
|--------|-------------|
| `--use-ssh` | Use SSH (`qm` commands) instead of Proxmox API. **Recommended** when API returns 401. |
| `--dry-run` | Show what would change; do not apply |
| `--vmids` | Comma-separated VM IDs (default: 192,193,194,195) |
| `--host` | Proxmox host (default from config: 192.168.0.202) |
| `--node` | Proxmox node (default: pve) |
| `--port` | Proxmox port (default: 8006) |

### Credentials

The script uses credentials from `.credentials.local`:

- `PROXMOX202_PASSWORD` (preferred)
- `PROXMOX_PASSWORD`
- `VM_PASSWORD`

Per `.cursor/rules/vm-credentials.mdc`, agents load credentials automatically and never ask for them.

## What the Script Does

1. Fetches VM config via SSH (`qm config <vmid>`)
2. Stops the VM if running
3. Deletes `scsi0` and `scsihw`
4. Adds `sata0` with the same underlying disk
5. Updates boot order (ide2 first if ISO attached, else sata0)

## Verification

After running the script:

1. Start the VM from Proxmox
2. Boot from Windows ISO (ide2)
3. Choose **Custom: Install Windows only**
4. The disk should appear and installation should complete

## Related

- `infra/csuite/provision_base.py` – new VMs use SATA for system disk
- `config/proxmox202_csuite.yaml` – C-Suite host, storage, ISO paths
- `infra/csuite/provision_ssh.py` – `pve_ssh_exec`, plink/paramiko fallbacks
