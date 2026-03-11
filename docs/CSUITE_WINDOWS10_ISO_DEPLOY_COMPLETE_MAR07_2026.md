# C-Suite Windows 10 ISO Deploy — Complete

**Date**: March 7, 2026
**Status**: Complete
**Related**: [CTO VM Blueprint](.cursor/plans/cto_vm_blueprint_bc9af924.plan.md), [Supabase Operational Backbone](.cursor/plans/supabase_operational_backbone_d160cd3a.plan.md)

## Overview

The Windows 10 22H2 ISO was obtained automatically, copied to Proxmox 202 (192.168.0.202), and all four C-Suite VMs (CEO, CFO, CTO, COO) were configured to boot from the installer. OpenClaw and the new Windows line can run immediately after completing Windows setup in each VM console.

## What Was Delivered

### 1. Script: `scripts/download_and_deploy_win10_iso.py`

Fully automated pipeline:

- Fetches [Fido.ps1](https://github.com/pbatard/Fido) (Microsoft ISO URL resolver)
- Runs Fido to obtain Windows 10 22H2 Pro English x64 download URL
- Downloads ISO to `data/iso/Win10_22H2_English_x64.iso`
- Uploads ISO to Proxmox 202 via Paramiko SFTP: `root@192.168.0.202:/var/lib/vz/template/iso/`
- Sets `windows_version: "10"` in `config/proxmox202_csuite.yaml`
- Runs `scripts/fix_csuite_windows_install.py` to attach ISO and set boot order for all VMs

### 2. ISO Location

| Location | Path |
|----------|------|
| Local (MAS repo) | `data/iso/Win10_22H2_English_x64.iso` (~5.8 GB) |
| Proxmox 202 | `/var/lib/vz/template/iso/Win10_22H2_English_x64.iso` |
| Proxmox config reference | `local:iso/Win10_22H2_English_x64.iso` |

### 3. C-Suite VMs Updated

| VM | VMID | Role | Boot Order | Status |
|----|------|------|------------|--------|
| CEO | 192 | CEO | ide2;scsi0 (ISO first) | Running, boots from installer |
| CFO | 193 | CFO | ide2;scsi0 | Running, boots from installer |
| CTO | 194 | CTO | ide2;scsi0 | Running, boots from installer |
| COO | 195 | COO | ide2;scsi0 | Running, boots from installer |

Each VM has the Win10 ISO attached on `ide2` and will boot from it until Windows is installed and the boot order is changed.

## How to Verify

1. **Proxmox UI**: Open https://192.168.0.202:8006 → VM 192/193/194/195 → Hardware → CD/DVD Drive shows `Win10_22H2_English_x64.iso`; Boot order = ide2 first.
2. **Console**: Open VM console → VM should boot into Windows 10 setup.
3. **Config**: `config/proxmox202_csuite.yaml` has `windows_version: "10"`.

## Re-run (If Needed)

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/download_and_deploy_win10_iso.py
```

- `--skip-download` — ISO already local
- `--skip-fix` — Don't run fix script (config/upload only)
- `--force` — Re-download even if ISO exists

## Next Steps

1. In Proxmox console for each VM, complete Windows 10 installation (language, product key skip, disk, user).
2. After Windows boots, install OpenClaw per C-Suite rollout docs.
3. Optional: Create a neutral base template (VMID 9100) from a fully configured Win10+OpenClaw VM for faster future rollouts.

## Related Documents

- [CSUITE_NEUTRAL_BASE_IMAGE_STRATEGY_MAR08_2026.md](./CSUITE_NEUTRAL_BASE_IMAGE_STRATEGY_MAR08_2026.md)
- [fix_csuite_windows_install.py](../scripts/fix_csuite_windows_install.py)
