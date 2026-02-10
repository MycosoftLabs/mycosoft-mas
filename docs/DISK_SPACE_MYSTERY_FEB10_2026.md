# Disk Space Mystery Investigation - Feb 10, 2026

## Problem
Windows Settings showing 3.2-3.7 TB in "System" category. User observed space jumping by 2 TB during scans.

## Investigation Summary

### C: Drive (8TB WD_BLACK SN850X on Disk 2)
| Metric | Value |
|--------|-------|
| Filesystem reports USED | 4.06 TB |
| Filesystem reports FREE | 3.21 TB |
| Visible files (dir /s) | 883 GB (1,840,377 files) |
| **DISCREPANCY** | **3.18 TB unaccounted** |

### Disk 1 Finding (4TB WD_BLACK SN850X)
- Has 3.7 TB in an "Unknown" LDM partition
- GPT Type: `{e6d6d379-f507-44c2-a23c-238f2a3df928}` (LDM Data)
- No drive letter, no filesystem
- Windows Settings may count this as "System" space

### Ruled Out
- Volume Shadow Copies (VSS) - vssadmin reports "No items found"
- Git LFS temp files - all .git/lfs/tmp directories clean
- Docker VHDX - only 97 GB, not sparse
- Temp folders - only 2.6 GB
- Recycle Bin - empty
- Hibernation file - not present
- pagefile.sys - only 16 GB

## Root Cause Analysis

### Issue 1: NTFS  Corruption (C: drive)
The NTFS filesystem's bitmap (which tracks allocated clusters) may be out of sync with actual file allocations. This can happen after:
- System crashes
- Power failures
- Heavy disk operations (like failed LFS downloads)

**Fix:** `chkdsk C: /F` (scheduled for next reboot)

### Issue 2: Orphaned LDM Partition (Disk 1)
A 3.7 TB partition exists with LDM (Logical Disk Manager) type but no filesystem. This was likely created by:
- A failed Storage Spaces setup
- Windows installation partition creation
- Dynamic disk conversion attempt

**Fix:** Delete partition via diskpart and create new NTFS volume

## Resolution Steps

1. **Reboot computer** - chkdsk /F scheduled to run on C:
2. **After reboot, check if C: used space decreased**
3. **Reclaim Disk 1 space** (optional):
   ```
   diskpart
   select disk 1
   select partition 3
   delete partition override
   create partition primary
   format fs=ntfs quick label="Data"
   assign letter=D
   ```

## Prevention

- LFS is fully disabled via .lfsconfig (concurrenttransfers = 0)
- Git config has filter.lfs.smudge = --skip
- Scheduled script runs hourly to clean any LFS temp files
- This incident was NOT caused by LFS

## Related Documents
- PERSONAPLEX_LFS_INCIDENT_AND_PREVENTION_FEB06_2026.md
- DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md
- GIT_CRISIS_AND_COMPREHENSIVE_FIX_FEB10_2026.md
