# Background Terminals and Unauthorized PowerShell Audit

**Date**: March 16, 2026  
**Status**: Complete  
**Scope**: Mycosoft CODE tree + Windows scheduled tasks; recurring visible terminals.

## Overview

Audit to find what was opening PowerShell/terminal windows every few minutes without user action, and to fix or document all scripts that start processes with visible windows.

## Root cause (fixed, then permanently disabled)

**Dev Server Watchdog** (`WEBSITE/website/scripts/dev-server-watchdog.ps1`):

- Ran in a loop every **30 seconds**.
- If the dev server (port 3010) was down for 3 consecutive checks (~90 s), it **restarted** the dev server.
- **Before fix:** It used `Start-Process -FilePath "cmd.exe" ... -WindowStyle Minimized`, which opened a **minimized CMD window** each time it restarted the server — matching “something opening every few minutes.”
- **Fix applied:** `-WindowStyle Minimized` was changed to **`-WindowStyle Hidden`**.
- **Permanently disabled (Mar 16, 2026):** Per user request, the Dev Server Watchdog has been turned off permanently:
  - Removed from `autostart-healthcheck.ps1` $Services array
  - Scheduled task `Mycosoft-DevServerWatchdog` unregistered (if it existed)
  - **Startup shortcut removed:** `Mycosoft-DevServerWatchdog.lnk` deleted from `%APPDATA%\...\Startup`
  - Removed from `autostart-services.mdc` registry
  - Any running watchdog process was killed

## Additional causes fixed (Mar 16, 2026)

**Scheduled tasks that were opening visible PowerShell windows:**

| Task | Frequency | Fix |
|------|-----------|-----|
| **Mycosoft-LFS-Cleanup** | **Hourly** | Added `-WindowStyle Hidden` — primary cause of "occasional" pop-ups |
| **Mycosoft-CursorChatBackup** | Daily 1:00 AM | Added `-WindowStyle Hidden` |
| **Mycosoft-Cursor-Chat-Backup** | Daily 12:00 PM | Added `-WindowStyle Hidden` |

Script comments in `backup-cursor-chats.ps1` and `prevent-lfs-bloat.ps1` updated so future reinstalls use Hidden. One-time fix script: `scripts/fix-visible-scheduled-tasks.ps1` (run as Admin if needed).

## Other scripts reviewed (no change needed)

| Script / Task | Frequency | Window behavior |
|---------------|-----------|------------------|
| **Mycosoft-CoworkVMWatchdog** | At logon + every 2 min | Task runs with `-WindowStyle Hidden`; `ensure-cowork-vm-watchdog.ps1` uses `Start-Service` only (no Start-Process). |
| **MYCOSOFT-Startup** | At logon | Runs `start-all-persistent.ps1` with `-WindowStyle Hidden`. |
| **dev-server-watchdog** (when started by start-watchdog.ps1 or register-dev-watchdog.ps1) | N/A | Launched with `-WindowStyle Hidden`; only the **child** (dev server) was Minimized — now Hidden. |
| **autostart-healthcheck.ps1** | Manual / on demand | Dev Server Watchdog entry uses Hidden when started via Start-Service path. |

## How the dev-server watchdog used to start (now disabled)

- **Scheduled task:** `Mycosoft-DevServerWatchdog` (if registered) — ran at logon. Task has been unregistered.
- **Startup / manual:** `start-watchdog.ps1` or autostart-healthcheck with `-StartMissing` previously started it. Watchdog has been removed from autostart-healthcheck; it is no longer started.

## Dev Server Watchdog — permanently off

The Dev Server Watchdog is **no longer started** by autostart-healthcheck, scheduled tasks, or agent protocols. To run the dev server, use `npm run dev:next-only` manually in an external terminal when needed.


## Memory / broader audit

A full “memory misallocation” and “everything that opens terminals” audit was not run this session. For that you can:

- Use Task Manager or `Get-Process | Sort-Object WorkingSet64 -Descending` to find high-RAM processes.
- Re-run a grep for `Start-Process` (and `WindowStyle`) across `.ps1`/`.cmd`/`.bat` if you add new scripts.

## Related

- `.cursor/rules/run-servers-externally.mdc` — dev server should run externally, not in Cursor.
- `WEBSITE/website/scripts/dev-server-watchdog.ps1` — no longer used; Dev Server Watchdog permanently disabled.
