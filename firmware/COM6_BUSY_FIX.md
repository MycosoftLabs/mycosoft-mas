# COM6 Busy - Quick Fix

## Problem
"Could not open COM6, the port is busy or doesn't exist"

## Quick Solutions

### Solution 1: Close Serial Monitor
1. **Close Serial Monitor** in Arduino IDE (click X on Serial Monitor window)
2. **Wait 2 seconds**
3. **Try upload again**

### Solution 2: Close All Arduino Windows
1. **Close ALL Arduino IDE windows**
2. **Task Manager → End all "Arduino IDE" processes**
3. **Restart Arduino IDE**
4. **Open your sketch**
5. **Try upload** (don't open Serial Monitor yet)

### Solution 3: Restart Arduino IDE
1. **File → Exit** (close completely)
2. **Wait 5 seconds**
3. **Restart Arduino IDE**
4. **Open sketch**
5. **Upload** (before opening Serial Monitor)

### Solution 4: Check for Other Programs
- **Close any terminal/command windows**
- **Close PuTTY, TeraTerm, or other serial programs**
- **Stop any Python scripts** using COM6

## Most Common Cause

**Serial Monitor is open!**

90% of the time, this is because Serial Monitor is still open. Close it and try again.

## After Upload

Once upload succeeds:
1. **Then** open Serial Monitor
2. **Set baud rate to 115200**
3. **Watch for output**

## Quick Command to Kill Arduino Processes

```powershell
Get-Process | Where-Object { $_.ProcessName -match "arduino" } | Stop-Process -Force
```

Then restart Arduino IDE.

