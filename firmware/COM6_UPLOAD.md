# Upload to COM6

## Current Status
- USB dock removed
- ESP32 plugged directly into PC
- New port: **COM6**

## Upload Steps

### 1. Select COM6 in Arduino IDE
- **Tools → Port → COM6**
- Make sure it's selected

### 2. Upload Firmware
- Click **Upload** button (→)
- Should work now!

### 3. If Upload Fails

**Try BOOT Button Method:**
1. **Hold BOOT button** on ESP32
2. **Click Upload** in Arduino IDE
3. **Keep holding BOOT** until you see "Connecting..."
4. **Release BOOT** when upload starts

**Or Lower Upload Speed:**
- **Tools → Upload Speed → 115200** (instead of 921600)
- Try upload again

## After Successful Upload

1. **Open Serial Monitor** (115200 baud)
2. **You should see:**
   - Startup message
   - MAC address
   - Sensor initialization
   - Telemetry every 10 seconds

3. **Test commands:**
   ```json
   {"cmd":"ping"}
   {"cmd":"status"}
   {"cmd":"i2c_scan"}
   ```

## Note About COM Ports

COM port numbers change when you:
- Plug into different USB port
- Use USB dock vs direct connection
- Unplug/replug device

**Always check which COM port Windows assigns!**

COM6 should work now - try uploading!

