# Upload Troubleshooting - COM Port Busy

## Problem
"Could not open COM3, the port is busy or doesn't exist"

## Solutions (Try in Order)

### Solution 1: Close Serial Monitor
1. **Close Serial Monitor** in Arduino IDE (if open)
2. **Close any other Arduino IDE windows** that might have Serial Monitor open
3. Try uploading again

### Solution 2: Stop MycoBrain Service
The MycoBrain service might be using COM3. Stop it temporarily:

```powershell
# Check if service is running
Get-Service | Where-Object { $_.DisplayName -match "mycobrain" }

# Or stop the Python service if running
# Find the process and stop it
```

Or manually:
1. Open Task Manager (Ctrl+Shift+Esc)
2. Look for Python processes
3. End any that might be using COM3
4. Try uploading again

### Solution 3: Close All Programs Using COM3
1. **Close Arduino IDE completely**
2. **Close any terminal/command windows**
3. **Close any serial monitor programs** (PuTTY, TeraTerm, etc.)
4. **Restart Arduino IDE**
5. Try uploading again

### Solution 4: Unplug and Replug USB
1. **Unplug the USB cable** from ESP32
2. **Wait 5 seconds**
3. **Plug it back in**
4. **Wait for Windows to recognize it** (check Device Manager)
5. **Try uploading again**

### Solution 5: Use Different USB Port
1. **Try a different USB port** on your computer
2. **Prefer USB 2.0 ports** (not USB 3.0) if available
3. **Avoid USB hubs** - connect directly to computer

### Solution 6: Hold BOOT Button During Upload
1. **Hold the BOOT button** on ESP32
2. **Click Upload** in Arduino IDE
3. **Keep holding BOOT** until you see "Connecting..."
4. **Release BOOT** when upload starts

### Solution 7: Manual Reset
1. **Press and hold BOOT button**
2. **Press and release RESET button** (while holding BOOT)
3. **Release BOOT button**
4. **Try uploading immediately**

## Quick Checklist

- [ ] Serial Monitor closed
- [ ] All Arduino IDE windows closed
- [ ] MycoBrain service stopped
- [ ] USB cable unplugged/replugged
- [ ] Different USB port tried
- [ ] BOOT button method tried
- [ ] Device Manager shows COM3 without errors

## After Successful Upload

Once uploaded, you can:
1. **Start MycoBrain service again**
2. **Open Serial Monitor** to see output
3. **Test commands**

## Most Common Fix

**90% of the time, this is because Serial Monitor is open!**

1. Close Serial Monitor
2. Try upload again
3. ✅ Should work!

