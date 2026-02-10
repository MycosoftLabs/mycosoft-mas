# Git Crisis and Comprehensive Fix – Feb 10, 2026

## Crisis Summary

All Git pushes are failing across **MAS**, **Website**, and **MINDEX** repos due to 4 critical configuration issues:

1. **Git LFS Configuration Blocks Pushes** – `.lfsconfig` has `concurrenttransfers = 0`, which is flagged as "unsafe" by Git LFS and prevents all LFS uploads
2. **Line Ending Chaos** – Missing or incomplete `.gitattributes` causing hundreds of "LF will be replaced by CRLF" warnings
3. **Incomplete .gitignore** – Database files, test artifacts, and build outputs not ignored
4. **Permission-Locked .pytest_cache** – Locked directories in MAS and MINDEX causing "Permission denied" errors

**Impact**: Cannot push to GitHub = cannot deploy from GitHub = entire deployment pipeline blocked.

---

## Root Cause Analysis

### Issue 1: Git LFS Configuration Crisis

**File**: `.lfsconfig` in MAS repo

**Current config**:
```ini
[lfs]
	fetchexclude = *
	concurrenttransfers = 0
```

**Why it exists**: Added Feb 6 to prevent Cursor's git integration from spawning git-lfs processes that filled the 8TB drive with 1.74TB of temp files.

**Why it blocks pushes**: Git LFS treats `concurrenttransfers = 0` as "unsafe" and refuses to upload ANY LFS files. The push hangs waiting for LFS upload that never completes.

**LFS files in repo**: 25+ PersonaPlex model files tracked by LFS (voices, tokenizers, etc.)

**Fix**: Change to `concurrenttransfers = 1` (minimum safe value) to allow pushes while keeping `fetchexclude = *` to prevent downloads.

---

### Issue 2: Line Ending Configuration Chaos

**Problem**: All modified Python, Markdown, and config files show "LF will be replaced by CRLF" warnings.

**Root cause**: 
- MAS has minimal `.gitattributes` (only 3 lines for shell scripts)
- Website has NO `.gitattributes` at all
- MINDEX has NO `.gitattributes` at all

**Why it matters**: 
- Hundreds of warning messages obscure real errors
- Files get modified on every checkout/commit creating false changes
- Cross-platform collaboration breaks (Linux VMs vs Windows dev)

**Fix**: Add comprehensive `.gitattributes` to all repos with proper line ending rules for each file type.

---

### Issue 3: Incomplete .gitignore

**Missing entries across repos**:

| Missing Entry | Repos | Impact |
|---------------|-------|--------|
| `*.db`, `*.db-shm`, `*.db-wal`, `*.db-journal` | MAS, Website, MINDEX | SQLite database files appear as untracked (e.g. `claude_code_queue.db`, `voice_feedback.db`) |
| `.pytest_cache/` | MAS, MINDEX | Pytest cache causing permission errors |
| `playwright-report/`, `test-results/` | Website | Test artifacts appear as untracked |
| `mindex.egg-info/` | MINDEX | Build artifact appears as untracked |
| `tsconfig.tsbuildinfo` | Website | Build cache appears as modified |

---

### Issue 4: Permission-Locked .pytest_cache

**Locations**:
- `MAS/mycosoft-mas/tests/.pytest_cache/`
- `MINDEX/mindex/.pytest_cache/`

**Error**: "warning: could not open directory '.pytest_cache/': Permission denied"

**Why**: Pytest creates cache with restrictive permissions, and when agents/processes run with different users/contexts, Git can't read them.

**Fix**: Delete the directories and add to `.gitignore`.

---

## Comprehensive Fix Plan

### Phase 1: Fix Git LFS (MAS repo only)

1. Update `.lfsconfig`:
   ```ini
   # LFS CONFIGURED FOR PUSH SUPPORT - Feb 10, 2026
   # fetchexclude prevents Cursor from auto-downloading large files
   # concurrenttransfers = 1 is minimum safe value to allow pushes
   [lfs]
   	fetchexclude = *
   	concurrenttransfers = 1
   ```

2. Update `.gitignore` comment for models line (remove strange spacing):
   ```
   # PersonaPlex models tracked by LFS
   models/personaplex-7b-v1/model.safetensors
   ```

---

### Phase 2: Fix Line Endings (All repos)

Create `.gitattributes` in **MAS**, **Website**, **MINDEX** with:

```gitattributes
# Auto-detect text files and normalize line endings to LF in repository
* text=auto eol=lf

# Explicitly declare text files
*.md text eol=lf
*.py text eol=lf
*.ts text eol=lf
*.tsx text eol=lf
*.js text eol=lf
*.jsx text eol=lf
*.json text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.toml text eol=lf
*.ini text eol=lf
*.cfg text eol=lf
*.txt text eol=lf
*.sh text eol=lf
*.bash text eol=lf
Dockerfile text eol=lf
Makefile text eol=lf

# Windows-specific files must have CRLF
*.ps1 text eol=crlf
*.bat text eol=crlf
*.cmd text eol=crlf

# Binary files
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.pdf binary
*.zip binary
*.tar binary
*.gz binary
*.tgz binary
*.safetensors binary
*.pt binary
*.pth binary
*.db binary
*.sqlite binary
*.dll binary
*.exe binary
*.so binary
*.dylib binary
```

**Rationale**: 
- Store everything as LF in repo (Linux VMs require LF)
- Auto-convert to CRLF on Windows checkout (if needed)
- Explicit CRLF only for PowerShell/batch scripts
- Mark binaries to prevent corruption

---

### Phase 3: Fix .gitignore (All repos)

#### MAS additions:

Add after Python section:
```gitignore
# SQLite databases and temp files
*.db
*.db-shm
*.db-wal
*.db-journal
*.sqlite
*.sqlite3

# Pytest cache
.pytest_cache/
.cache/

# Mypy cache
.mypy_cache/
.dmypy.json
dmypy.json

# Ruff cache
.ruff_cache/

# Claude Code queue
data/claude_code_queue.db
data/voice_feedback.db
data/*.db
```

Update models line (remove strange character spacing):
```gitignore
# PersonaPlex models tracked by LFS
models/personaplex-7b-v1/model.safetensors
```

#### Website additions:

Add after Python section:
```gitignore
# Test artifacts
playwright-report/
test-results/
.playwright/

# SQLite databases
*.db
*.db-shm
*.db-wal
*.db-journal

# Build cache
tsconfig.tsbuildinfo
.tsbuildinfo

# Pytest cache (for services/)
.pytest_cache/
```

#### MINDEX additions:

Add after existing entries:
```gitignore
# SQLite databases
*.db
*.db-shm
*.db-wal
*.db-journal

# Pytest cache
.pytest_cache/

# Python build artifacts
*.egg-info/
build/
dist/

# Test output
test_output.txt
```

---

### Phase 4: Clean Permission-Locked Directories

For **MAS** and **MINDEX**:

```powershell
# Force delete pytest cache (run with admin if needed)
Remove-Item -Recurse -Force tests\.pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
```

For **Website**:

```powershell
# Delete test artifacts
Remove-Item -Recurse -Force playwright-report -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force test-results -ErrorAction SilentlyContinue
```

---

### Phase 5: Verify Git Status is Clean

After all fixes, run in each repo:

```powershell
# Check what will be committed
git status

# Should show only:
# - Modified: .lfsconfig (MAS only)
# - Modified/New: .gitattributes (all repos)
# - Modified: .gitignore (all repos)
# - Deleted: .pytest_cache/ (if Git was tracking it)
# - Untracked files should be MINIMAL (only legitimate new files)
```

---

### Phase 6: Test Push (One Repo at a Time)

Start with **MINDEX** (simplest, no LFS):

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex
git add .gitattributes .gitignore
git commit -m "Fix Git configuration: add .gitattributes and update .gitignore"
git push origin main
```

Then **Website**:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
git add .gitattributes .gitignore
git commit -m "Fix Git configuration: add .gitattributes and update .gitignore"
git push origin main
```

Finally **MAS** (has LFS, most complex):

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
git add .lfsconfig .gitattributes .gitignore
git commit -m "Fix Git configuration: update .lfsconfig to allow pushes, add comprehensive .gitattributes, update .gitignore"
git push origin main
```

**Expected**: Push should complete in 5-30 seconds without hanging.

---

## Post-Fix Verification

After all pushes succeed:

1. **Verify on GitHub**: Check that commits appear in all three repos
2. **Test VM deploy**: 
   - Website: On VM 187 run `git pull` and rebuild container
   - MAS: On VM 188 run `git pull` and rebuild orchestrator
3. **Verify no warnings**: Run `git status` in each repo – should be clean with no warnings
4. **Monitor Cursor**: Ensure git-lfs processes don't spawn and fill drive again

---

## Prevention Measures

1. **Add to .cursor/rules/git-configuration.mdc** (new file):
   - Document the LFS configuration and why concurrenttransfers = 1
   - Reference this crisis document
   - Rule: NEVER set concurrenttransfers to 0

2. **Add .gitattributes check to regression-guard agent**:
   - Verify .gitattributes exists in all repos
   - Verify it has proper line ending rules

3. **Add .pytest_cache to all Python repo templates**:
   - Ensure it's in .gitignore from the start

4. **Monitor drive space**:
   - Set up alert if `.git/lfs/tmp/` grows beyond 10GB
   - Document the LFS temp bloat issue in ops docs

---

## Related Documents

- `docs/DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md` – Original LFS bloat crisis
- `docs/SYSTEM_STATUS_AND_PURGE_FEB09_2026.md` – Notes MAS push failures
- `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md` – Deploy pipeline that's now unblocked

---

## Success Criteria

✅ All three repos can push to GitHub without hanging  
✅ No "LF will be replaced by CRLF" warnings  
✅ No "Permission denied" errors  
✅ Git status is clean (only legitimate new files shown as untracked)  
✅ VMs can pull from GitHub and deploy  
✅ LFS temp bloat does not return  

---

**Status**: Ready to apply fixes (this document)  
**Next**: Apply Phase 1-6 fixes to all three repos
