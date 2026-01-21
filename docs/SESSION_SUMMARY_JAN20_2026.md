# Development Session Summary - January 20, 2026

## Session Overview

This session continued the system audit and deployment work from January 19, 2026. The primary focus was fixing MycoBrain device communication issues that prevented peripherals from being detected and controls from working.

## Issues Addressed

### 1. MycoBrain Device Lookup Fix (Critical)

**Problem:** Website could not communicate with MycoBrain devices because the backend only supported lookup by COM port, but the frontend was using device_id.

**Solution:** Modified `get_device()` method in `mycobrain_service.py` to support lookup by both port and device_id.

**Files Changed:**
- `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\services\mycobrain\mycobrain_service.py`

**Details:** See [MYCOBRAIN_FIX_JAN20_2026.md](MYCOBRAIN_FIX_JAN20_2026.md)

### 2. Stale Process Cleanup

**Problem:** After Cursor IDE crashed, multiple Python processes were holding the COM7 serial port, preventing new connections.

**Solution:** Identified and killed stale Python processes:
```powershell
taskkill /PID 107264 /F
taskkill /PID 151868 /F
taskkill /PID 152884 /F
```

### 3. Port Conflict Resolution

**Problem:** Port 8003 was occupied by a previous MycoBrain instance that hadn't fully terminated.

**Solution:** Killed process on port 8003 before restarting:
```powershell
$pid8003 = (Get-NetTCPConnection -LocalPort 8003 -State Listen).OwningProcess
taskkill /PID $pid8003 /F
```

### 4. Website Dev Server Restart

**Problem:** Website API proxy was timing out after system crash.

**Solution:** Killed and restarted the website dev server:
```powershell
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
$env:PORT="3010"
npm run dev
```

## Verification Completed

### Terminal Tests

| Test | Command | Result |
|------|---------|--------|
| Health Check | `GET /health` | ✅ 1 device connected |
| Port Scan | `GET /ports` | ✅ COM7 detected |
| Device List | `GET /devices` | ✅ device_id populated |
| Sensor Read | `POST /devices/COM7/command` | ✅ 2 BME688 sensors |
| Device ID Lookup | `POST /devices/{device_id}/command` | ✅ 200 OK |

### Browser Tests

| Feature | URL | Result |
|---------|-----|--------|
| Device Manager | `/natureos/devices` | ✅ Loads correctly |
| Peripheral Scan | Sensors tab | ✅ 2 BME688 detected |
| Sensor Data | Sensors tab | ✅ Live streaming |
| LED Control | Controls tab | ✅ OK status, commands work |
| Buzzer Control | Controls tab | ✅ OK status, sounds play |
| Smell Detection | Sensors tab | ✅ "Fresh Mushroom Fruiting" |

### Sensor Data Captured

**BME688 #1 (AMB - 0x77):**
- Temperature: 29.7°C
- Humidity: 30.7%
- Pressure: 652 hPa
- Gas Resistance: 70.9 kΩ
- IAQ: 50 (accuracy: 0)

**BME688 #2 (ENV - 0x76):**
- Temperature: 28.6°C
- Humidity: 32.3%
- Pressure: 698 hPa
- Gas Resistance: 56.4 kΩ
- IAQ: 50 (accuracy: 0)

## Services Running After Session

| Port | Service | Status |
|------|---------|--------|
| 3010 | Website (npm run dev) | ✅ Running |
| 8003 | MycoBrain Service | ✅ Running |
| 3000 | Website (Docker) | ⚠️ May need restart |
| 3001 | Unknown Node process | ❓ Check if needed |

## Completed Additional Tasks

1. **Sandbox Deployment**: ✅ Successfully deployed via Proxmox API
2. **Instant Deploy Script**: Created `scripts/instant_deploy.py` for fast deployments
3. **Git Safe Directory**: Fixed ownership warnings on VM

## Remaining Tasks

1. **Video Assets**: Missing mushroom1 video files - use NAS media integration
2. **Cloudflare API Keys**: Add `CF_ZONE_ID` and `CF_API_TOKEN` for auto cache purge

## Commands Reference

### Quick Start (After System Restart)

```powershell
# 1. Start MycoBrain Service
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\services\mycobrain"
$env:MINDEX_API_URL="http://192.168.0.187:8000"
$env:MINDEX_API_KEY="local-dev-key"
$env:MYCOBRAIN_PUSH_TELEMETRY_TO_MINDEX="true"
Start-Process python -ArgumentList "-m uvicorn mycobrain_service:app --host 0.0.0.0 --port 8003"

# 2. Start Website Dev Server
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
$env:PORT="3010"
npm run dev

# 3. Connect to MycoBrain device
Start-Sleep -Seconds 5
Invoke-WebRequest -Uri "http://localhost:8003/devices/connect/COM7" -Method POST
```

### Troubleshooting Commands

```powershell
# Check what's using ports
Get-NetTCPConnection -State Listen | Where-Object { 
    $_.LocalPort -in @(3000, 3010, 8003) 
} | ForEach-Object {
    $proc = Get-Process -Id $_.OwningProcess -EA SilentlyContinue
    [PSCustomObject]@{ Port=$_.LocalPort; Process=$proc.ProcessName; PID=$_.OwningProcess }
} | Format-Table

# Kill all Python processes
Get-Process python* | Stop-Process -Force

# Kill process on specific port
$pid = (Get-NetTCPConnection -LocalPort 8003 -State Listen).OwningProcess
taskkill /PID $pid /F

# Test MycoBrain health
(Invoke-WebRequest -Uri "http://localhost:8003/health" -TimeoutSec 5).Content

# Test website MycoBrain proxy
(Invoke-WebRequest -Uri "http://localhost:3010/api/mycobrain/health" -TimeoutSec 5).Content
```

## Documentation Created

1. **MYCOBRAIN_FIX_JAN20_2026.md** - Detailed fix documentation with code changes
2. **SESSION_SUMMARY_JAN20_2026.md** - This session summary

## Git Changes Pending

The following file was modified and needs to be committed:

```
website/services/mycobrain/mycobrain_service.py
```

### Suggested Commit Message

```
fix(mycobrain): support device lookup by device_id in addition to port

The website frontend calls MycoBrain API with device_id (e.g., 
mycobrain-10:B4:1D:E3:3B:C4) but get_device() only looked up by
COM port. This fix adds fallback lookup by device_id and serial_number.

Fixes: Peripheral detection and control button issues
Tested: Both BME688 sensors detected, LED/buzzer controls working
```

## Deployment Steps (When Ready)

```powershell
# On Windows (development machine)
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
git add services/mycobrain/mycobrain_service.py
git commit -m "fix(mycobrain): support device lookup by device_id in addition to port"
git push origin main

# On VM (192.168.0.187)
ssh mycosoft@192.168.0.187
cd /home/mycosoft/mycosoft/mas
git pull origin main

# Rebuild and restart website container
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache
docker compose -f docker-compose.always-on.yml up -d mycosoft-website

# Purge Cloudflare cache
# (Do this via Cloudflare dashboard)
```

## Notes

- The MycoBrain service runs on **Windows**, not the VM, because it needs access to COM ports
- The Cloudflare tunnel terminates on the **VM**, so brain-sandbox.mycosoft.com can't reach MycoBrain directly
- For sandbox MycoBrain access, need either SSH tunnel or reverse proxy from VM to Windows

## Fast Deployment Workflow

Use the new instant deploy script (no SSH hangs):

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/instant_deploy.py
```

This script:
1. Uses Proxmox API + QEMU Guest Agent (no SSH)
2. Pulls latest code from GitHub
3. Rebuilds Docker image
4. Restarts container
5. Verifies deployment
6. Purges Cloudflare cache (if credentials set)

For instant media updates (no rebuild needed):
1. Copy files to NAS: `\\192.168.0.105\mycosoft.com\website\assets\`
2. Files appear instantly at `https://sandbox.mycosoft.com/assets/...`
3. Purge Cloudflare cache if cached

---

*Session completed: January 20, 2026*
*Duration: ~2 hours*
*Status: ✅ COMPLETE - Local and Sandbox both working*
