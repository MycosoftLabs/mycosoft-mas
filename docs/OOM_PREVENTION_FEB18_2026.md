# Cursor OOM Prevention – Feb 18, 2026

Single source of truth to **prevent Cursor from crashing with Out of Memory** and to recover when it happens.

---

## 1. What we changed (already in repo)

### Workspace settings (`mycosoft.code-workspace`)
- **files.exclude**: node_modules, .next, out, dist, build, .vercel, coverage, __pycache__, .pio (so Cursor doesn’t load them).
- **search.exclude**: same plus .git, *.log (so search doesn’t index them).
- **files.watcherExclude**: node_modules, .next, out, dist, build, .git (so file watchers use less memory).
- **typescript.tsserver.maxTsServerMemory**: 2048 (cap TS server at 2GB so it doesn’t grow unbounded).

### MAS `.cursorignore`
- MAS repo already has a full `.cursorignore` (node_modules, .next, Python/TS caches, logs, large binaries). Keeps Cursor indexing light in this repo.

### Dev server and GPU
- **Never run the website dev server or GPU services inside Cursor.** Run them from **Windows Terminal or CMD outside Cursor**:
  - `cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
  - `scripts\start-dev.cmd`
- See `WEBSITE/website/docs/DEV_SERVER_CRASH_FIX_FEB12_2026.md`.

---

## 2. What you must do (checklist)

### Before opening Cursor (every time if you had OOM before)
1. **Kill stale GPU processes** (they use a lot of RAM):
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts
   .\dev-machine-cleanup.ps1 -KillStaleGPU
   ```
2. **Optional:** Shut down WSL to free vmmem (if you don’t need Docker/WSL):
   ```powershell
   .\dev-machine-cleanup.ps1 -ShutdownWSL
   ```
   or `wsl --shutdown`

### When using Cursor
3. **Do not run the dev server or GPU services in Cursor’s terminal.** Use an external terminal and run `scripts\start-dev.cmd` (website) there.
4. **Remove unneeded workspace folders** if you only work in one or two repos: File > Remove Folder from Workspace. Fewer roots = less indexing = less memory.

### If a repo doesn’t have `.cursorignore`
5. Add a file named **`.cursorignore`** in that repo’s root (e.g. `WEBSITE/website/.cursorignore`) with at least:
   ```
   node_modules/
   .next/
   out/
   dist/
   build/
   *.log
   coverage/
   ```

---

## 3. If Cursor still hits OOM

1. **Close Cursor.**
2. Run cleanup:
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts
   .\dev-machine-cleanup.ps1 -KillStaleGPU -ShutdownWSL
   ```
3. **Reopen Cursor** and open only the folders you need (e.g. just MAS + WEBSITE).
4. Ensure **no dev server or GPU is started from inside Cursor**; run them from an external terminal only.

---

## 4. Reference

| Item | Location |
|------|----------|
| Workspace file | `mycosoft.code-workspace` (in CODE folder) |
| Cleanup script | `MAS/mycosoft-mas/scripts/dev-machine-cleanup.ps1` |
| Dev server (external) | `WEBSITE/website/scripts/start-dev.cmd` |
| OOM rule for agents | `MAS/mycosoft-mas/.cursor/rules/oom-prevention.mdc` |
| Dev server crash doc | `WEBSITE/website/docs/DEV_SERVER_CRASH_FIX_FEB12_2026.md` |
