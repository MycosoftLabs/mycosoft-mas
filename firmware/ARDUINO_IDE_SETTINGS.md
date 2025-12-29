# Arduino IDE Settings for ESP32-S3 Upload

## Critical Settings

### 1. Board Settings
- **Board**: `ESP32-S3 Dev Module`
- **Upload Speed**: `115200` (or `9600` if 115200 fails)
- **CPU Frequency**: `240MHz`
- **Flash Frequency**: `80MHz`
- **Flash Mode**: `QIO`
- **Flash Size**: `4MB (32Mb)`
- **Partition Scheme**: `Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)`
- **Core Debug Level**: `None`
- **PSRAM**: `Disabled` (unless your board has PSRAM)
- **Port**: `COM4` (or your Side-A port)

### 2. Upload Settings
- **Erase All Flash Before Sketch Upload**: `Enabled` ⚠️ **IMPORTANT**
- **Programmer**: `Esptool`

### 3. Before Upload
1. **Close Serial Monitor** (if open)
2. **Put device in boot mode** (see BOOT_MODE_FIX.md)
3. **Click Upload** immediately after boot mode

## Boot Mode Procedure (CRITICAL)

**You MUST do this EVERY TIME before upload:**

1. **Unplug USB** from Side-A
2. **Wait 30 seconds** (let capacitors discharge)
3. **Hold BOOT button** (keep holding)
4. **Plug USB back in** (still holding BOOT)
5. **Hold BOOT for 5 full seconds**
6. **Release BOOT**
7. **Wait 2 seconds**
8. **Click Upload in Arduino IDE IMMEDIATELY**

## If Upload Still Fails

### Try Lower Speed
- Change **Upload Speed** to `9600`
- This is slower but more reliable

### Try Different Method
- Hold **BOOT** button
- Press and release **RESET** button (while holding BOOT)
- Keep holding **BOOT** for 3 seconds
- Release **BOOT**
- Upload immediately

### Check COM Port
- Make sure **COM4** is correct
- Check Device Manager if port changed
- Close any other programs using COM4

## Success Indicators

When boot mode works:
- Arduino IDE shows: "Connecting..." then "Writing at 0x..."
- Progress bar appears
- "Done uploading" message

When boot mode fails:
- "Connecting......................................" (forever)
- "Failed to connect to ESP32-S3: No serial data received"

## Troubleshooting

### "Port COM4 is busy"
- Close Serial Monitor
- Close any other programs using COM4
- Restart Arduino IDE

### "Failed to connect"
- Device not in boot mode - follow boot mode procedure
- Try different USB cable
- Try different USB port (USB 2.0 preferred)

### "Upload successful but device doesn't work"
- Open Serial Monitor (115200 baud)
- Press RESET button on device
- Should see output


