# C-Suite Windows 10 Fallback — Complete

**Date:** 2026-03-07  
**Status:** Complete  
**Related:** `config/proxmox202_csuite.yaml`, `infra/csuite/provision_csuite.py`, `scripts/check_csuite_windows_compatibility.py`

## Summary

C-Suite VMs on Proxmox 202 (192.168.0.202) assumed Windows 11, which requires UEFI, TPM 2.0, and stricter hardware. Windows 10 works with legacy BIOS, no TPM, and lower requirements. The system now supports both versions via config and provisioning.

## Changes

### 1. Compatibility Check Script

**File:** `scripts/check_csuite_windows_compatibility.py`

- SSHs to Proxmox 202 and checks:
  - OVMF (UEFI) availability
  - swtpm (software TPM) availability
  - Windows 10 and 11 ISO presence
- Recommends Win10 or Win11 based on host capabilities
- `--force-win10` forces Win10 recommendation regardless of host

**Usage:**
```bash
python scripts/check_csuite_windows_compatibility.py
python scripts/check_csuite_windows_compatibility.py --force-win10
```

### 2. Config: `config/proxmox202_csuite.yaml`

- `windows_version: "10"` — Use Windows 10 (default for compatibility)
- `windows_version: "11"` — Use Windows 11 when host supports it
- `iso_path_win10` — Path to Windows 10 ISO on Proxmox
- `iso_path` — Path to Windows 11 ISO (kept for Win11)

### 3. Provisioning: `infra/csuite/provision_csuite.py`

- **`get_build_source()`** now returns:
  - `iso_path` — Resolved for Win10 (`iso_path_win10`) or Win11 (`iso_path`) based on `windows_version`
  - `ostype` — `"win10"` or `"win11"` for Proxmox `qm create`
- **`_create_windows_vm_ssh()`** passes `ostype` to `pve_ssh_create_blank_vm()`

### 4. Provisioning: `infra/csuite/provision_ssh.py`

- **`pve_ssh_create_blank_vm()`** accepts `ostype` (default `"win10"`)
- Removed hardcoded `--ostype win11`

### 5. Fix Script: `scripts/fix_csuite_windows_install.py`

- Uses `get_build_source()` from `provision_csuite` instead of raw config
- Attaches the correct ISO (Win10 or Win11) and sets boot order for installer

## Switching Between Windows 10 and 11

1. Edit `config/proxmox202_csuite.yaml`:
   ```yaml
   windows_version: "10"   # Use Windows 10 (works on all hosts)
   # or
   windows_version: "11"   # Use Windows 11 (requires OVMF + swtpm)
   ```

2. Ensure the correct ISO exists on Proxmox:
   - Win10: path from `iso_path_win10`
   - Win11: path from `iso_path`

3. Re-run provisioning or `fix_csuite_windows_install.py` as needed.

## Verification

- Run `python scripts/check_csuite_windows_compatibility.py` to see host recommendations.
- Provision new VMs with `windows_version: "10"` in config.
- Run `python scripts/fix_csuite_windows_install.py` to attach ISO and fix boot order for existing VMs.
