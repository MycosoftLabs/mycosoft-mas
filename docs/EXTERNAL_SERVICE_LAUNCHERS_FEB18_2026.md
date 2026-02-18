# External Service Launchers (Feb 18, 2026)

Services that run in **external windows**—independent of Cursor. Close Cursor anytime; services keep running.

## Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `start-mycobrain-external.ps1` | `MAS/scripts/` | MycoBrain service on port 8003 |
| `start-dev-external.ps1` | `WEBSITE/website/scripts/` | Website dev server on port 3010 |
| `start-all-dev-services-external.ps1` | `MAS/scripts/` | Starts both in separate windows |

## Usage

**Option 1: Double-click**
- Navigate to the script in Explorer
- Double-click to run (opens new PowerShell window)

**Option 2: From PowerShell**
```powershell
# MycoBrain only
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\start-mycobrain-external.ps1

# Dev server only
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
.\scripts\start-dev-external.ps1

# Both
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\start-all-dev-services-external.ps1
```

## MycoBrain Auto-Start on Boot

To install scheduled task (requires **Run as Administrator**):
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\mycobrain-service.ps1 -Schedule
```

## Current Status (as of creation)

- MycoBrain: port 8003 — healthy, 2 devices
- Dev server: port 3010 — OK
- APIs: `/api/mycobrain`, `/api/devices/discover` — working
- Device pages: `/natureos/devices`, `/natureos/devices/network` — loading
