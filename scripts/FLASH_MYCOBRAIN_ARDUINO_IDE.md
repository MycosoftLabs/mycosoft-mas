# Flash MycoBrain Production Firmware - Arduino IDE

## Quick Flash Instructions

The device is currently in **BOOTLOADER MODE** and needs firmware flashed.

### Steps:

1. **Open Arduino IDE**
   - Launch Arduino IDE (1.8.19 or later)

2. **Open Production Firmware**
   - File → Open
   - Navigate to: `firmware\MycoBrain_SideA\MycoBrain_SideA_Production.ino`
   - Click Open

3. **Select Board**
   - Tools → Board → ESP32 Arduino → **ESP32S3 Dev Module**

4. **Configure Settings** (CRITICAL - Use these exact settings)
   - **USB CDC on boot**: Enabled
   - **USB DFU on boot**: Enabled (requires USB OTG mode)
   - **USB Firmware MSC on boot**: Disabled
   - **USB Mode**: Hardware CDC and JTAG
   - **JTAG Adapter**: Integrated USB JTAG
   - **PSRAM**: OPI PSRAM
   - **CPU Frequency**: 240 MHz
   - **WiFi Core Debug Level**: None
   - **Arduino runs on core**: 1
   - **Events run on core**: 1
   - **Flash Mode**: QIO @ 80 MHz
   - **Flash Size**: 16 MB
   - **Partition Scheme**: 16MB flash, 3MB app / 9.9MB FATFS
   - **Upload Speed**: 921600
   - **Upload Port**: **COM6** (or your device port)
   - **Erase all flash before upload**: Disabled

5. **Upload Firmware**
   - Click **Upload** button (→)
   - Wait for compilation and upload to complete
   - Should see "Done uploading" message

6. **Verify Device**
   - Open Serial Monitor (Tools → Serial Monitor)
   - Set baudrate to **115200**
   - Should see device initialization messages
   - Send: `status` and should get response

### After Flashing:

Once firmware is flashed, the device should:
- Boot automatically
- Send initialization messages
- Respond to commands
- Stream telemetry every 10 seconds

### Test Commands:

```
mode machine
dbg off
fmt json
scan
status
```

### If Upload Fails:

1. **Device in bootloader mode**: Hold BOOT button, press RESET, release BOOT
2. **Port not found**: Check Device Manager, try different USB port
3. **Upload timeout**: Lower upload speed to 115200
4. **Permission error**: Close other programs using COM port

---

**Current Status**: Device on COM6, in bootloader mode, ready for firmware upload
