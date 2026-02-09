# PersonaPlex Git LFS Incident: Full 8TB Drive, Data Loss, and Prevention

**Date:** February 6, 2026  
**Status:** RESOLVED  
**Severity:** Critical -- caused complete drive fill, Cursor crash, loss of all chat history  
**Relates to:** PersonaPlex model files in `models/personaplex-7b-v1/`

---

## Summary

PersonaPlex's model files (voice models, safetensors, tokenizer) were tracked by Git LFS. Cursor's background git integration silently spawned hundreds of `git-lfs` processes that attempted to download these files. Each failed download left a 7-15 GB temporary file that was never cleaned up. Over days/weeks, **1,572 failed downloads accumulated 1.74 TB of garbage** in `.git/lfs/tmp/`, filling the entire 8 TB drive and crashing Cursor, which destroyed all chat history.

This document explains exactly what happened, what was done, and what every developer must know to prevent it from happening again -- on this repo or any repo that contains large model files.

---

## Table of Contents

1. [What Happened](#1-what-happened)
2. [PersonaPlex Files That Triggered It](#2-personaplex-files-that-triggered-it)
3. [The Cascade: How 30 GB of Models Became 1.74 TB of Garbage](#3-the-cascade)
4. [Damage](#4-damage)
5. [What Was Cleaned](#5-what-was-cleaned)
6. [Permanent Fixes Applied](#6-permanent-fixes-applied)
7. [Rules for PersonaPlex Development Going Forward](#7-rules-for-personaplex-development-going-forward)
8. [Rules for ANY Repo with Large Files](#8-rules-for-any-repo-with-large-files)
9. [How to Detect This Problem Early](#9-how-to-detect-this-problem-early)
10. [How to Recover If It Happens Again](#10-how-to-recover-if-it-happens-again)
11. [Scripts and Scheduled Tasks](#11-scripts-and-scheduled-tasks)

---

## 1. What Happened

### Timeline

1. **At some point before Feb 6, 2026:** The PersonaPlex 7B model was added to the repo under `models/personaplex-7b-v1/`. The model's HuggingFace-style `.gitattributes` file (inside that directory) configured Git LFS to track 33 file patterns including `*.safetensors`, `*.pt`, `*.tgz`, `*.model`, `*.bin`, and many others.

2. **Every time Cursor was open:** Cursor's built-in git integration ran background operations (`git status`, `git fetch`, `git diff`, etc.) automatically and continuously. Because Git LFS filters were configured, every git operation triggered `git-lfs filter-process` and `git-lfs smudge`, which attempted to download the LFS-tracked files from GitHub.

3. **Each download failed or was interrupted** (likely due to network issues, GitHub rate limits, or the files being large). Each failure left a temporary file in `.git/lfs/tmp/` that was **never cleaned up** by Git LFS.

4. **Cursor respawned git-lfs processes immediately** after each one finished or failed. At any given moment, there were 10-20+ simultaneous `git` and `git-lfs` processes running. This happened 24/7 whenever Cursor was open.

5. **Over days/weeks, 1,572 failed temp files accumulated**, each averaging ~1.1 GB. Total: **1,740 GB (1.74 TB)** in `.git/lfs/tmp/` alone.

6. **On Feb 6, 2026, the 8 TB drive hit 0.2 GB free.** Cursor crashed, reported "out of memory," and its chat database (`state.vscdb`) was corrupted/reset. All chat history was permanently lost (no cloud sync, no shadow copies available).

---

## 2. PersonaPlex Files That Triggered It

The following files in `models/personaplex-7b-v1/` were tracked by Git LFS (via the `.gitattributes` in that directory):

| File | Size | Type |
|------|------|------|
| `model.safetensors` | 15.6 GB | Main PersonaPlex 7B model weights |
| `tokenizer-e351c8d8-checkpoint125.safetensors` | 358 MB | Tokenizer weights |
| `tokenizer_spm_32k_3.model` | ~1 MB | SentencePiece tokenizer |
| `voices.tgz` | 6 MB | Compressed voice pack |
| `voices/NATF0.pt` through `voices/NATM3.pt` | ~50 MB each | 8 natural voice models |
| `voices/VARF0.pt` through `voices/VARM4.pt` | ~50 MB each | 10 variable voice models |
| `dist.tgz` | 14.4 GB | Distribution archive |
| `figures/*.png` | ~1 MB each | 3 result figures |
| **Total** | **~30 GB** | **25 LFS-tracked files** |

The `.gitattributes` also tracked dozens of file extensions generically (`*.bin`, `*.onnx`, `*.pkl`, `*.tar.*`, `*.zip`, etc.) meaning **any future file matching those patterns would also trigger LFS downloads**.

---

## 3. The Cascade

How 30 GB of model files created 1.74 TB of garbage:

```
PersonaPlex model files (30 GB)
  → .gitattributes has filter=lfs rules (33 patterns)
    → Cursor opens workspace
      → Cursor runs background git operations (continuous)
        → git invokes git-lfs filter-process
          → git-lfs tries to download 30 GB of files
            → Download fails (network, rate limit, timeout)
              → 7-15 GB temp file left in .git/lfs/tmp/
                → git-lfs exits
                  → Cursor immediately respawns git operations
                    → git-lfs tries again, fails again, leaves another temp file
                      → LOOP REPEATS 1,572 TIMES
                        → 1,740 GB of garbage
                          → 8 TB drive full
                            → Cursor crash
                              → Chat database destroyed
```

**Key insight:** The problem was not the model files themselves (30 GB). The problem was that `.gitattributes` told git to use LFS filters, and Cursor's git integration ran those filters **continuously in the background** without any rate limiting or cleanup.

---

## 4. Damage

| Impact | Detail |
|--------|--------|
| Disk space consumed | 1,740 GB in `.git/lfs/tmp/` |
| Drive state | 8 TB drive at 0.2 GB free (100% full) |
| Cursor crash | "Out of memory" -- editor became unusable |
| Chat history | **All chats permanently lost** (local-only storage, no backups, no shadow copies) |
| Machine performance | Severely degraded while drive was full |
| Additional garbage found | 587 GB of Google Drive failed uploads (`.tmp.driveupload`) -- also triggered by the full drive causing upload failures |

---

## 5. What Was Cleaned

| Item | Size freed |
|------|-----------|
| `.git/lfs/tmp/` (1,572 failed download temp files) | 1,740 GB |
| `.git/lfs/objects/` (old LFS objects, pruned + re-accumulated) | ~182 GB |
| `.tmp.driveupload` (Google Drive failed uploads) | 587 GB |
| Recycle Bin | 52 GB |
| HuggingFace model cache (`~/.cache/huggingface`) | 49 GB |
| Morgan2 duplicate AppData | 47 GB |
| Hibernation file (disabled) | 128 GB |
| pip cache | 14 GB |
| Docker prune (unused images/containers) | 9 GB |
| **Total recovered** | **~2,808 GB** |

**Drive after cleanup:** 3,209 GB free (was 0.2 GB free)

---

## 6. Permanent Fixes Applied

### Fix 1: LFS filter rules removed from models/.gitattributes

**File:** `models/personaplex-7b-v1/.gitattributes`

**Before (caused the problem):**
```
*.safetensors filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
*.tgz filter=lfs diff=lfs merge=lfs -text
*.model filter=lfs diff=lfs merge=lfs -text
*.bin filter=lfs diff=lfs merge=lfs -text
... (33 patterns total)
```

**After (fixed):**
```
# LFS tracking DISABLED Feb 6, 2026
# All LFS filter rules have been removed from this file.
```

This is the **single most important fix**. Without `filter=lfs` in `.gitattributes`, git never invokes `git-lfs` at all.

### Fix 2: .lfsconfig added to repo root

**File:** `.lfsconfig`
```ini
[lfs]
    fetchexclude = *
    concurrenttransfers = 0
```

Even if someone accidentally re-adds LFS rules, this config prevents any fetching.

### Fix 3: Local git config

```
filter.lfs.smudge = git-lfs smudge --skip -- %f
filter.lfs.process = git-lfs filter-process --skip
filter.lfs.required = false
lfs.fetchexclude = *
lfs.concurrenttransfers = 0
```

The `--skip` flag tells git-lfs to do nothing when invoked. `required = false` means git won't error if LFS fails.

### Fix 4: Global git config

All global `filter.lfs.*` entries removed so no repo on this machine triggers LFS unless explicitly configured.

### Fix 5: Hourly cleanup task

Windows Task Scheduler runs `scripts/prevent-lfs-bloat.ps1` every hour. It:
- Kills any `git-lfs` processes (they should never be running)
- Deletes anything in `.git/lfs/tmp/`, `.git/lfs/objects/`, `.git/lfs/cache/`
- Re-checks and re-applies the git config if it was reset
- Re-checks `models/personaplex-7b-v1/.gitattributes` and removes `filter=lfs` if it reappears

### Fix 6: Daily chat backup task

Windows Task Scheduler runs `scripts/backup-cursor-chats.ps1` daily at noon. It copies `%APPDATA%\Cursor\User\workspaceStorage` and settings to `E:\CursorBackups\` (E: drive has 1.8 TB free). Keeps 30 days of backups.

---

## 7. Rules for PersonaPlex Development Going Forward

### NEVER re-enable Git LFS in any Mycosoft repo used with Cursor

Cursor's background git integration will immediately start downloading LFS files in an infinite loop. There is no way to configure Cursor to skip LFS operations.

### PersonaPlex model files: use external storage, not git

| Do this | Not this |
|---------|----------|
| Store models on NAS (`\\192.168.0.105\mycosoft.com\models\`) | Commit models to git (even with LFS) |
| Store models on HuggingFace Hub and download on demand | Track with `filter=lfs` in `.gitattributes` |
| Use `.gitignore` to exclude `*.safetensors`, `*.pt`, etc. | Let git track binary model files |
| Mount model directory at runtime (`-v /models:/models`) | Include models in Docker build context |
| Document model download URL in README | Assume models are available from git clone |

### If you must add large files to a repo

1. **Add them to `.gitignore`** -- never commit them to git
2. **Never use Git LFS** in any repo opened with Cursor
3. **If the repo already has `.gitattributes` with `filter=lfs`** (e.g. from HuggingFace clone), **remove those rules immediately**
4. **Check `.git/lfs/tmp/` weekly** -- if it contains anything, something is wrong

### PersonaPlex model deployment

The PersonaPlex 7B model should be deployed via:
1. Download from HuggingFace Hub to the target machine (VM, Docker host)
2. Mount as a Docker volume: `-v /path/to/models:/app/models`
3. Never include in git history or Docker image layers

The `models/personaplex-7b-v1/` directory in this repo should be:
- Listed in `.gitignore` (already done)
- Listed in `.cursorignore` (already done)
- Excluded from Docker build context via `.dockerignore`

---

## 8. Rules for ANY Repo with Large Files

These rules apply to every Mycosoft repo, not just MAS:

### Before opening any repo in Cursor

1. **Check for `.gitattributes` files** containing `filter=lfs`
2. **If found, remove the `filter=lfs` rules** or delete the `.gitattributes` file
3. **Check `.git/lfs/` directory size** -- if it exists and is growing, LFS is active

### When cloning repos from HuggingFace

HuggingFace repos always have `.gitattributes` with LFS rules. If you clone one into a Cursor workspace:

```powershell
# Clone without LFS
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/...

# Or on Windows
set GIT_LFS_SKIP_SMUDGE=1
git clone https://huggingface.co/...

# Then immediately remove LFS rules
del models\*\.gitattributes
# Or replace the file contents with a comment
```

### When adding submodules or subtrees

If the submodule has LFS, the parent repo will also trigger LFS downloads. Check and remove `filter=lfs` from all `.gitattributes` in submodules.

### For the Website repo, MINDEX repo, or any other Mycosoft repo

Apply the same checks. If any repo has large files:
- Use `.gitignore`, not LFS
- Store large files on NAS, HuggingFace, or cloud storage
- Document download URLs in the repo README

---

## 9. How to Detect This Problem Early

### Warning signs

| Sign | What it means |
|------|--------------|
| Multiple `git-lfs` processes in Task Manager | LFS is actively downloading |
| `.git/lfs/tmp/` folder growing | Failed downloads accumulating |
| Disk space dropping without obvious cause | LFS garbage filling drive |
| Cursor becoming slow or crashing | Drive is full or nearly full |
| `git status` is very slow | LFS filter-process is running |

### Monitoring

The scheduled task `Mycosoft-LFS-Cleanup` runs hourly and catches this. You can also run manually:

```powershell
# Quick check
Get-ChildItem "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.git\lfs" -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum | ForEach-Object { Write-Host "$([math]::Round($_.Sum/1GB,2)) GB in .git/lfs" }

# Check for git-lfs processes
Get-Process -Name "git-lfs" -ErrorAction SilentlyContinue | Measure-Object | ForEach-Object { Write-Host "$($_.Count) git-lfs processes running" }

# Full cleanup
.\scripts\prevent-lfs-bloat.ps1
```

---

## 10. How to Recover If It Happens Again

### If the drive fills up

1. **Close Cursor** (to stop git-lfs from respawning)
2. **Delete `.git/lfs/tmp/`**: `Remove-Item -Recurse -Force .git\lfs\tmp`
3. **Delete `.git/lfs/objects/`**: `Remove-Item -Recurse -Force .git\lfs\objects`
4. **Kill any git-lfs processes**: `taskkill /f /im git-lfs.exe`
5. **Check and remove `filter=lfs` from all `.gitattributes` files** in the repo
6. **Re-open Cursor** only after confirming LFS is disabled

### If Cursor chats are lost

1. **Check for backups** in `E:\CursorBackups\` (if the daily backup task was running)
2. **Restore `state.vscdb`** from the backup to `%APPDATA%\Cursor\User\workspaceStorage\<hash>\`
3. **Restart Cursor** -- chats should reappear
4. **If no backup exists**: chats are unrecoverable. Cursor does not sync to the cloud.

---

## 11. Scripts and Scheduled Tasks

| Script | Purpose | Schedule |
|--------|---------|----------|
| `scripts/prevent-lfs-bloat.ps1` | Kills git-lfs, cleans LFS data, re-applies config | Hourly (Task: Mycosoft-LFS-Cleanup) |
| `scripts/backup-cursor-chats.ps1` | Backs up Cursor chat DB + settings to E:\ | Daily at noon (Task: Mycosoft-Cursor-Chat-Backup) |
| `scripts/find-disk-usage.ps1` | Reports disk usage for debugging space issues | Manual |
| `scripts/dev-machine-cleanup.ps1` | Kills stale GPU processes, optionally shuts down WSL | Manual |

---

## Related Documents

| Document | Description |
|----------|-------------|
| `docs/DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md` | Initial recovery doc (written during the incident) |
| `docs/PERSONAPLEX_FULL_INTEGRATION_FEB03_2026.md` | PersonaPlex integration architecture |
| `docs/DEPLOYMENT_PERSONAPLEX_V7_FEB03_2026.md` | PersonaPlex deployment guide |
| `docs/WHY_DEV_MACHINE_SLOW_FEB06_2026.md` | GPU process cleanup (related performance issue) |
| `.lfsconfig` | LFS disabled config (committed to repo) |
| `models/personaplex-7b-v1/.gitattributes` | LFS rules removed (committed to repo) |

---

## Key Takeaway

**Never use Git LFS in any repo opened with Cursor.** Cursor's background git integration will trigger LFS downloads in an infinite loop, each failure leaving multi-GB temp files that are never cleaned up. For PersonaPlex and all other large model files, use external storage (NAS, HuggingFace Hub, cloud) and `.gitignore`. This incident cost 1.74 TB of disk space and all Cursor chat history -- it must never happen again.
