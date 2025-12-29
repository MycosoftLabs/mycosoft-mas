# Quick Upload Guide - Free COM Port

## Problem
COM3 is busy - can't upload firmware

## Quick Fix (2 Steps)

### Step 1: Stop MycoBrain Service
Run this PowerShell command:
```powershell
.\scripts\stop_mycobrain_service.ps1
```

Or manually:
```powershell
# Find and stop Python process using port 8003
Get-Process python* | Where-Object { (netstat -ano | findstr "8003" | findstr $_.Id) } | Stop-Process -Force
```

### Step 2: Upload Firmware
1. **In Arduino IDE:**
   - Tools → Port → **COM3**
   - Click **Upload** (→)
   - ✅ Should work now!

## After Upload

### Restart MycoBrain Service
```powershell
cd services/mycobrain
python mycobrain_dual_service.py
```

Or if using Docker:
```bash
docker-compose up mycobrain-service
```

## Alternative: Close Serial Monitor

If the service isn't running, the issue might be:
- **Serial Monitor is open** in Arduino IDE
- **Close Serial Monitor** (click X on Serial Monitor window)
- Try upload again

## Most Common Causes

1. ✅ **Serial Monitor open** → Close it
2. ✅ **MycoBrain service running** → Stop it
3. ✅ **Another Arduino IDE window** → Close all Arduino windows
4. ✅ **Python script using COM3** → Stop it

## Quick Checklist

- [ ] Serial Monitor closed
- [ ] MycoBrain service stopped
- [ ] All Arduino IDE windows closed
- [ ] Try upload to COM3

**99% of the time, it's Serial Monitor or the service!**

