# PowerShell Pop-up Audit — Mar 16, 2026

**Status:** Complete  
**Purpose:** List every source that can open a visible PowerShell (or other) window; document fixes so pop-ups stop.

---

## Summary of fixes applied (Mar 16, 2026)

| Source | Issue | Fix |
|--------|--------|-----|
| **cursor-chat-backup.ps1** | Scheduled task created without `-WindowStyle Hidden` → midnight backup opened a visible PowerShell window | Added `-WindowStyle Hidden` to the task action in `Install-Schedule` |
| **fix-visible-scheduled-tasks.ps1** | Used wrong task name `Mycosoft-Cursor-Chat-Backup` and wrong script path | Updated to `Mycosoft-CursorChatBackup` and `cursor-chat-backup.ps1` so existing backup task can be fixed |
| **voice-test-readiness.ps1** | Started dev server with `-WindowStyle Normal` | Changed to `-WindowStyle Hidden` |
| **start-all-dev-services-external.ps1** | Opened two visible PowerShell windows for MycoBrain + dev server | Both launches now use `-WindowStyle Hidden`; services run in background |

---

## Sources that can open PowerShell or a window

### 1. Scheduled tasks (Windows Task Scheduler)

| Task name | Script | When it runs | Fixed? |
|-----------|--------|----------------|--------|
| **Mycosoft-CursorChatBackup** | `scripts\cursor-chat-backup.ps1` | Daily (e.g. midnight) | Yes — script now creates task with Hidden; run fix script to update existing task |
| **Mycosoft-LFS-Cleanup** | `scripts\prevent-lfs-bloat.ps1` | Per schedule | fix-visible-scheduled-tasks.ps1 updates this task to Hidden |

**Action for you:** Run the fix script **once as Administrator** so existing scheduled tasks get Hidden:

```powershell
# Right-click PowerShell -> Run as Administrator, then:
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts
.\fix-visible-scheduled-tasks.ps1
```

### 2. Scripts that start other processes

| Script | What it starts | Fixed? |
|--------|----------------|--------|
| **cursor-chat-backup.ps1** (Install-Schedule) | Creates scheduled task that runs this script | Yes — task action now includes `-WindowStyle Hidden` |
| **dev-server-watchdog.ps1** | Starts dev server (npm) in a child process | Yes — already used Hidden |
| **start-dev-and-crep-external.ps1** | Dev + CREP servers | Yes — uses Hidden |
| **start-mycobrain-external.ps1** | MycoBrain service | Yes — uses Hidden |
| **mycobrain-service.ps1** (start) | MycoBrain Python process | Yes — uses Hidden |
| **voice-test-readiness.ps1** | Dev server for voice readiness check | Yes — changed to Hidden |
| **start-all-dev-services-external.ps1** | MycoBrain + website dev server | Yes — both launches now Hidden |
| **autostart-healthcheck.ps1** (StartMissing) | Starts services via their StartScript (e.g. mycobrain-service.ps1, notion-sync.ps1); Python started with `Start-Process -WindowStyle Hidden` | Python: Hidden. Other scripts (e.g. notion-sync) run in-process when invoked with `&`; no extra window unless a script does Start-Process without Hidden |

### 3. Rules / docs that tell agents to start processes

- **run-servers-externally.mdc** — Start-Process examples updated to use Hidden where appropriate.
- **dev-server-3010.mdc** — Dev server started externally; watchdog uses Hidden.
- **agent-must-execute-operations.mdc** — No change; agents execute; scripts they call are the ones fixed above.

---

## How to verify

1. **Scheduled tasks:** In Task Scheduler, open **Mycosoft-CursorChatBackup** → Actions → Edit. The Arguments should include `-WindowStyle Hidden`. If not, run `fix-visible-scheduled-tasks.ps1` as Administrator.
2. **Backup at midnight:** After the next run, you should not see a PowerShell window (backup runs hidden).
3. **Voice readiness / start-all:** Run `voice-test-readiness.ps1` or `start-all-dev-services-external.ps1`; no visible PowerShell windows should open for the started processes.

---

## If you still see a pop-up

1. Note the **window title** or any text (e.g. “full audit”, “health check”).
2. Check **Task Scheduler** for any Mycosoft-related tasks that run a `.ps1` or `powershell.exe` and ensure their Action arguments include `-WindowStyle Hidden`.
3. Search the repo for that text:  
   `rg "full audit|health check" --type-add 'ps1:*.ps1' -t ps1 .`
4. If it’s an agent or rule that runs a script, ensure that script (or the task that runs it) uses `-WindowStyle Hidden` when starting PowerShell.

---

## Related

- **fix-visible-scheduled-tasks.ps1** — Run as Admin to add Hidden to known scheduled tasks.
- **autostart-services.mdc** — Lists autostart services; startup uses the scripts above (now Hidden where applicable).
