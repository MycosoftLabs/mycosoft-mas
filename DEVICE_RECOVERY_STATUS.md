# MycoBrain Device Recovery Status

**Date**: December 30, 2024  
**Status**: ⚠️ **DEVICE IN BOOTLOADER MODE - NEEDS FIRMWARE FLASH**

---

## Current Device Status

### Connection
- **Port**: COM6
- **Baud Rate**: 115200
- **Status**: ✅ Port accessible
- **Device State**: ⚠️ **BOOTLOADER MODE**

### Bootloader Message
```
rst:0x15 (USB_UART_CHIP_RESET),boot:0x0 (DOWNLOAD(USB/UART0))
Saved PC:0x40041a76
waiting for down
```

**Meaning**: Device is waiting for firmware to be uploaded via USB.

---

## Required Action

### Flash Production Firmware

**Option 1: Arduino IDE (Recommended)**
1. Open `firmware\MycoBrain_SideA\MycoBrain_SideA_Production.ino` in Arduino IDE
2. Select Board: **ESP32S3 Dev Module**
3. Select Port: **COM6**
4. Configure settings (see `scripts\FLASH_MYCOBRAIN_ARDUINO_IDE.md`)
5. Click **Upload**

**Option 2: PlatformIO**
- Requires setting up `src/` folder structure
- More complex, but automated

---

## After Flashing

Once firmware is successfully flashed:

1. **Device will boot automatically**
2. **Should see initialization messages in Serial Monitor**
3. **Device will respond to commands**
4. **Telemetry will stream every 10 seconds**

### Test Sequence

```bash
# 1. Start MycoBrain service
.\scripts\start_mycobrain_service.ps1

# 2. Connect device
Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM6" -Method POST

# 3. Test commands
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM6/command" `
  -Method POST -Body '{"command":"status"}' -ContentType "application/json"

# 4. Initialize machine mode
# Send: mode machine, dbg off, fmt json, scan, status
```

---

## Troubleshooting

### If Upload Fails

1. **Device not in bootloader**: 
   - Hold BOOT button
   - Press and release RESET button
   - Release BOOT button
   - Device should show "waiting for down"

2. **Port not found**:
   - Check Device Manager
   - Try different USB port
   - Unplug and replug USB cable

3. **Upload timeout**:
   - Lower upload speed to 115200
   - Try holding BOOT button during upload

4. **Permission error**:
   - Close other programs using COM6
   - Close Serial Monitor
   - Close Arduino IDE Serial Monitor if open

---

## Next Steps

1. ⏳ **Flash firmware** (Arduino IDE or PlatformIO)
2. ⏳ **Verify device boots** (check Serial Monitor)
3. ⏳ **Start MycoBrain service** (`.\scripts\start_mycobrain_service.ps1`)
4. ⏳ **Connect device** (via API)
5. ⏳ **Test commands** (status, scan, etc.)
6. ⏳ **Verify telemetry** (should stream automatically)

---

**Current Status**: Device ready for firmware flash on COM6
