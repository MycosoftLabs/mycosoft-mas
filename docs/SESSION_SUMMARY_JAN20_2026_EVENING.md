# Development Session Summary - January 20, 2026 (Evening Session)

## Session Overview

**Time**: Evening Session  
**Agent**: Cursor AI Assistant  
**Focus Areas**: MycoBrain device control fix, Sandbox deployment investigation

---

## Issues Resolved

### 1. MycoBrain COM7 Controls Not Working (CRITICAL FIX)

**Problem**: MycoBrain controls visible in localhost UI but commands had no effect on the physical board connected to COM7.

**Symptoms**:
- LED control buttons visible but board LED didn't respond
- Buzzer commands sent but no sound from device
- Sensor data showing but was stale (3+ hours old)
- Service reported device "connected" but telemetry frozen

**Root Cause**: **Duplicate MycoBrain Service Running**

A second MycoBrain service was running on port **18003** (in addition to the main one on 8003). This duplicate service had exclusive access to COM7, blocking the main service from communicating with the device.

```
Process Analysis:
├── PID 149704: Main MycoBrain service on port 8003 ← UI was talking to this
├── PID 148432: Multiprocessing spawn (child of 149704)
├── PID 158640: DUPLICATE MycoBrain on port 18003 ← Holding COM7!
└── PID 107264: vm_upgrade_and_deploy.py (unrelated)
```

**Diagnostic Commands Used**:
```powershell
# Check what's listening on MycoBrain ports
netstat -ano | findstr ":8003 :18003"

# Identify Python processes
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CommandLine

# Check COM port availability
python -c "import serial.tools.list_ports; [print(f'{p.device}: {p.description}') for p in list(serial.tools.list_ports.comports())]"
```

**Solution**:
```powershell
# 1. Kill duplicate service
Stop-Process -Id 158640 -Force

# 2. Reconnect main service to COM7
Invoke-WebRequest -Uri "http://localhost:8003/devices/connect/COM7" -Method POST

# 3. Verify with test command
$body = @{command=@{cmd="coin"}} | ConvertTo-Json -Depth 3
Invoke-WebRequest -Uri "http://localhost:8003/devices/COM7/command" -Method POST -Body $body -ContentType "application/json"
```

**Verification**:
| Test | Result |
|------|--------|
| Connect to COM7 | ✅ Success |
| Coin buzzer command | ✅ Audible sound from device |
| NeoPixel LED (red) | ✅ LED turned red |
| Fresh telemetry | ✅ 22.8°C, 37.4% humidity |
| Uptime reset | ✅ Device showing fresh uptime |

---

### 2. Sandbox Deployment Investigation

**Problem**: Website on sandbox.mycosoft.com showing "Application error: a client-side exception has occurred"

**Investigation Findings**:

1. **VM Container Status**: Website container running but with old code
   ```
   mycosoft-always-on-mycosoft-website-1   Up 2 hours (healthy)
   ```

2. **Git Status**: Code pulled successfully
   ```
   HEAD is now at 2b8cc3f feat: security compliance updates, MycoBrain service updates
   ```

3. **Compose File Location Issue**: 
   - Script expected: `/opt/mycosoft/docker-compose.always-on.yml`
   - Actual location: `/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml`
   - Only file present: `/opt/mycosoft/docker-compose.yml`

**Action Required**: Container needs rebuild from correct compose file location. Another agent may be working on this per user indication.

---

## Services Status After Session

| Port | Service | Status | Notes |
|------|---------|--------|-------|
| 3010 | Website Dev Server | ✅ Running | Background process |
| 8003 | MycoBrain Service | ✅ Running | PID 149704, COM7 connected |
| 18003 | Duplicate Service | ❌ Killed | Was blocking COM7 |

---

## Key Insights & Lessons Learned

### Insight 1: Port Conflict Detection Pattern

When MycoBrain controls show in UI but don't affect the physical device:
1. First check if **multiple services** are running on different ports
2. The service holding the COM port exclusively wins
3. Use `netstat -ano | findstr "python\|8003\|18003"` to diagnose

### Insight 2: Stale Telemetry Indicator

When `last_message_time` is significantly in the past but device shows `connected: true`:
- The connection object exists but serial communication is blocked
- Check for port-locking processes
- Disconnect + reconnect may not work until blocker is killed

### Insight 3: Compose File Locations on VM

The VM has multiple potential compose file locations:
```
/opt/mycosoft/docker-compose.yml           # Simplified production
/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml  # Full always-on stack
```

Always verify which file to use before deploying.

---

## Scripts Created

### Deploy Sandbox Script
**Path**: `scripts/deploy_sandbox_now.py`

Python script using Paramiko for SSH-based deployment:
- Connects to VM (192.168.0.187)
- Pulls latest code
- Attempts rebuild and restart
- Shows container logs and health check

---

## Documentation Created This Session

1. **SESSION_SUMMARY_JAN20_2026_EVENING.md** - This document
2. **STAFF_BRIEFING_JAN20_2026.md** - Non-technical summary for staff
3. **MYCOBRAIN_TROUBLESHOOTING_GUIDE.md** - Troubleshooting reference

---

## Pending Tasks

| Task | Priority | Assigned To |
|------|----------|-------------|
| Rebuild sandbox website container | High | Another agent (per user) |
| Verify login/NatureOS on sandbox | High | After container rebuild |
| Fix MycoBrain on sandbox | Medium | Requires Windows → VM routing |

---

## Quick Reference Commands

### Check for Duplicate MycoBrain Services
```powershell
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | 
    Where-Object { $_.CommandLine -match "mycobrain" } | 
    Select-Object ProcessId, CommandLine
```

### Force Reset MycoBrain Connection
```powershell
# Disconnect
Invoke-WebRequest -Uri "http://localhost:8003/devices/disconnect/COM7" -Method POST

# Wait
Start-Sleep -Seconds 3

# Reconnect
Invoke-WebRequest -Uri "http://localhost:8003/devices/connect/COM7" -Method POST
```

### Test All Controls
```powershell
# Coin sound
$body = @{command=@{cmd="coin"}} | ConvertTo-Json -Depth 3
Invoke-WebRequest -Uri "http://localhost:8003/devices/COM7/command" -Method POST -Body $body -ContentType "application/json"

# Red LED
$body = @{r=255; g=0; b=0; mode="solid"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8003/devices/COM7/neopixel" -Method POST -Body $body -ContentType "application/json"

# Green LED
$body = @{r=0; g=255; b=0; mode="solid"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8003/devices/COM7/neopixel" -Method POST -Body $body -ContentType "application/json"
```

---

*Session completed: January 20, 2026*  
*Duration: ~30 minutes*  
*Status: MycoBrain working locally, sandbox deployment pending*
