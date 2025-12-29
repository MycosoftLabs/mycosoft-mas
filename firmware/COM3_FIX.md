# COM3 Upload Fix - Port Busy Error

## Current Error
"Could not open COM3, the port is busy or doesn't exist"
"PermissionError(13, 'A device attached to the system is not functioning.'"

## Solutions (Try Each)

### Solution 1: Close ALL Arduino IDE Windows
1. **Close ALL Arduino IDE windows** (there are multiple open!)
2. **Task Manager → End all "Arduino IDE" processes**
3. **Restart Arduino IDE**
4. **Open your sketch fresh**
5. Try upload

### Solution 2: Use BOOT Button Method
1. **Hold BOOT button** on ESP32 (keep holding)
2. **Press and release RESET button** (while holding BOOT)
3. **Click Upload** in Arduino IDE
4. **Keep holding BOOT** until you see "Connecting..."
5. **Release BOOT** when upload starts

### Solution 3: Unplug/Replug USB
1. **Unplug USB cable** from ESP32
2. **Wait 10 seconds**
3. **Plug back in**
4. **Wait for Windows to recognize** (check Device Manager)
5. **Try upload immediately**

### Solution 4: Try Different USB Port
1. **Unplug from current USB port**
2. **Plug into different USB port** (prefer USB 2.0)
3. **Avoid USB hubs** - connect directly
4. **Check new COM port number** (might change)
5. **Select new port in Arduino IDE**

### Solution 5: Restart Arduino IDE
1. **Close Arduino IDE completely**
2. **Wait 5 seconds**
3. **Restart Arduino IDE**
4. **Open sketch: File → Open → firmware/MycoBrain_SideA/MycoBrain_SideA.ino**
5. **Tools → Port → COM3**
6. **Try upload**

### Solution 6: Check Device Manager
1. **Win+X → Device Manager**
2. **Expand "Ports (COM & LPT)"**
3. **Find COM3**
4. **If it has yellow triangle:**
   - Right-click → Update driver
   - Or: Right-click → Uninstall device
   - Unplug/replug USB
   - Windows will reinstall driver

### Solution 7: Lower Upload Speed
1. **Tools → Upload Speed → 115200** (instead of 921600)
2. **Try upload**

### Solution 8: Use esptool Directly
If Arduino IDE keeps failing, use esptool directly:

```bash
# Find your .bin file location (Arduino shows it during compile)
# Then:
esptool.py --chip esp32s3 --port COM3 --baud 115200 write_flash 0x0 firmware.bin
```

## Most Likely Fix

**Multiple Arduino IDE windows are open!**

I see you have MANY Arduino IDE processes running:
- Arduino IDE (multiple instances)
- arduino-cli
- arduino-language-server
- serial-discovery

**Close ALL of them:**
1. Task Manager (Ctrl+Shift+Esc)
2. End all "Arduino IDE" processes
3. End "arduino-cli" process
4. End "serial-discovery" process
5. Restart Arduino IDE fresh
6. Try upload

## Quick Command to Kill All Arduino Processes

```powershell
Get-Process | Where-Object { $_.ProcessName -match "arduino" } | Stop-Process -Force
```

Then restart Arduino IDE and try again!

