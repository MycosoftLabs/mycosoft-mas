# C-Suite Windows Execution Complete (Mar 7, 2026)

**Date:** March 7, 2026  
**Status:** Complete  
**Related:** `docs/CSUITE_WINDOWS10_FALLBACK_MAR07_2026.md`, `config/proxmox202_csuite.yaml`

---

## Summary

Ran the full C-Suite Windows fix pipeline on Proxmox 202 (192.168.0.202). All four VMs (CEO 192, CFO 193, CTO 194, COO 195) now have the Windows 11 installer ISO attached and are booting from it. Manual Windows setup must be completed in each VM’s Proxmox console.

---

## Steps Executed

### 1. Compatibility Check

```powershell
python scripts/check_csuite_windows_compatibility.py
```

**Result:** Pass. OVMF, swtpm, Win11 ISO present. Win10 ISO not present.

### 2. Config Change (Win10 → Win11)

`config/proxmox202_csuite.yaml` was updated:

- **Before:** `windows_version: "10"` (ISO `local:iso/Win10_22H2_English_x64.iso` not on host)
- **After:** `windows_version: "11"` (ISO `local:iso/Win11_24H2_English_x64.iso` present)

### 3. Fix Script Dry-Run

```powershell
python scripts/fix_csuite_windows_install.py --dry-run
```

**Result:** Would attach ISO and set boot for VMs 192, 193, 194, 195.

### 4. Fix Script Execution

```powershell
python scripts/fix_csuite_windows_install.py
```

**Result:** Success for all four VMs.

```
Fixing VM 192 (ceo): attach ISO, set boot order...
  OK: ISO attached, boot order=ide2;scsi0 ✓ VM started. Boot from Windows installer.
Fixing VM 194 (cto): attach ISO, set boot order...
  OK: ISO attached, boot order=ide2;scsi0 ✓ VM started. Boot from Windows installer.
Fixing VM 193 (cfo): attach ISO, set boot order...
  OK: ISO attached, boot order=ide2;scsi0 ✓ VM started. Boot from Windows installer.
Fixing VM 195 (coo): attach ISO, set boot order...
  OK: ISO attached, boot order=ide2;scsi0 ✓ VM started. Boot from Windows installer.
Done. Each VM will boot from Windows installer. Complete setup in Proxmox console.
```

---

## Environment

| Item | Value |
|------|-------|
| Proxmox host | 192.168.0.202:8006 |
| Auth | SSH (`CSUITE_USE_SSH=1`) |
| ISO used | `local:iso/Win11_24H2_English_x64.iso` |
| Config | `config/proxmox202_csuite.yaml` |

---

## Next Steps for Staff

1. Open Proxmox UI: `https://192.168.0.202:8006`
2. For each VM (192, 193, 194, 195):
   - Open **Console**
   - Follow the Windows 11 installer (region, language, license, disk, user)
   - Finish setup and log in to the desktop
3. After Windows is installed:
   - Detach the ISO (or boot from disk) so the VM boots from the system disk
   - Run the OpenClaw/bootstrap scripts per `docs/CSUITE_OPENCLAW_GOLDEN_IMAGE_MAR07_2026.md`

---

## Reverting to Windows 10

To use Windows 10 instead:

1. Obtain `Win10_22H2_English_x64.iso` and copy it to Proxmox 202:  
   `/var/lib/vz/template/iso/Win10_22H2_English_x64.iso`
2. Set in `config/proxmox202_csuite.yaml`:
   ```yaml
   windows_version: "10"
   ```
3. Re-run: `python scripts/fix_csuite_windows_install.py`

---

## Files Touched

| File | Change |
|------|--------|
| `config/proxmox202_csuite.yaml` | `windows_version: "10"` → `"11"` |
| `docs/CSUITE_WINDOWS_EXECUTION_COMPLETE_MAR07_2026.md` | New |

---

## Verification

- [x] Compatibility check passed
- [x] Config updated to Win11 (ISO exists)
- [x] Fix script ran successfully
- [x] All four VMs have ISO attached and boot order set
- [x] All four VMs started and booting from Windows installer
- [ ] Manual Windows setup in Proxmox console (staff)
- [ ] OpenClaw/bootstrap per golden image doc (staff)
