# Cowork VM (PlotCore) Continuity and Watchdog

**Date:** March 4, 2026  
**Status:** Implemented  
**Related:** `docs/CLAUDE_COWORK_VM_TROUBLESHOOTING_MAR03_2026.md`, `scripts/ensure-cowork-vm-watchdog.ps1`, `scripts/install-cowork-vm-watchdog.ps1`

---

## Why This Matters

Claude Cowork (PlotCore) powers company automation:

- COO, Secretary, HR automations
- Hourly, half-hourly, daily scheduled co-work
- Tasks, assignments, staff workflows

When the Cowork VM service stops, automation stops. Manual restart is not acceptable. This document describes the **always-on continuity** solution.

---

## Components

### 1. CoworkVMService

- **What:** Windows service that runs the PlotCore VM used by Claude Desktop.
- **Where:** Installed with Claude Desktop (Cowork).
- **Check:** `Get-Service CoworkVMService`

### 2. Watchdog Script

- **Path:** `scripts/ensure-cowork-vm-watchdog.ps1`
- **Behavior:**
  - Checks if `CoworkVMService` exists
  - If not Running → starts it and sets StartupType to Automatic
  - Logs actions to `%LOCALAPPDATA%\Mycosoft\cowork-watchdog\watchdog.log` (last ~500 lines)
- **Silent:** Only logs when it has to fix something; no log when service is already running

### 3. Scheduled Task

- **Name:** `Mycosoft-CoworkVMWatchdog`
- **Triggers:**
  - At user logon
  - Every 2 minutes (repeats for 365 days; re-run install yearly to refresh)
- **Action:** Runs `ensure-cowork-vm-watchdog.ps1` hidden
- **Settings:** Runs on batteries, starts when available, restarts up to 3 times if it fails

---

## Installation

**Must run as Administrator.**

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\install-cowork-vm-watchdog.ps1
```

This will:

1. Remove any existing task
2. Create the scheduled task
3. Create the log directory
4. Run the watchdog once (to fix immediately if service is down)

---

## Verification

```powershell
# Task exists and is ready
Get-ScheduledTask -TaskName "Mycosoft-CoworkVMWatchdog"

# Service is running
Get-Service CoworkVMService

# Watchdog log (only exists after a fix attempt)
Get-Content "$env:LOCALAPPDATA\Mycosoft\cowork-watchdog\watchdog.log" -Tail 20
```

---

## Recovery Flow

1. **Service stops** (reboot, crash, manual stop).
2. Within **2 minutes** (or at next logon), the scheduled task runs the watchdog.
3. Watchdog detects service not Running → starts it → sets Automatic.
4. Cowork automation resumes.

---

## Manual Fix (If Needed)

```powershell
# One-time fix
Start-Service CoworkVMService
Set-Service CoworkVMService -StartupType Automatic

# Or run the watchdog manually
.\scripts\ensure-cowork-vm-watchdog.ps1
```

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| Task not running | Re-run `install-cowork-vm-watchdog.ps1` as Administrator |
| Service won't start | See `docs/CLAUDE_COWORK_VM_TROUBLESHOOTING_MAR03_2026.md` |
| CoworkVMService not found | Claude Desktop / Cowork may not be installed; install from claude.ai/download |
| Log not created | Normal when service is already running; log only appears after a fix |

---

## Files

| File | Purpose |
|------|---------|
| `scripts/ensure-cowork-vm-watchdog.ps1` | Watchdog logic |
| `scripts/install-cowork-vm-watchdog.ps1` | Task installation (run elevated) |
| `%LOCALAPPDATA%\Mycosoft\cowork-watchdog\watchdog.log` | Action log |
