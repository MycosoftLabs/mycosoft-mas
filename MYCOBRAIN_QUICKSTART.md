# MycoBrain Integration - Quick Start Guide

## Immediate Setup (Right Now)

### Step 1: Start the MycoBrain Service

**Option A: PowerShell Script (Recommended)**
```powershell
.\scripts\start_mycobrain_service.ps1
```

**Option B: Manual Start**
```powershell
cd services\mycobrain
python mycobrain_dual_service.py
```

The service will start on **http://localhost:8003**

### Step 2: Scan for USB Devices

```powershell
python scripts\scan_usb_devices.py
```

This will show all COM ports. Look for:
- COM3, COM4, COM5, COM6, COM7 (or similar)
- Devices with VID 0x303A (Espressif ESP32)
- USB Serial Device descriptions

### Step 3: Connect Devices via Dashboard

1. Open your browser to: **http://localhost:3001/natureos/devices**
2. Click the **"MycoBrain Devices"** tab
3. Click **"Scan Ports"** to refresh available ports
4. For each ESP32 device:
   - Click **"Connect Side-A"** for the first USB-C port
   - Click **"Connect Side-B"** for the second USB-C port

### Step 4: View Real-Time Telemetry

Once connected:
- Select a device from the list
- Telemetry updates every 2 seconds automatically
- You'll see:
  - Temperature (BME688)
  - Humidity (BME688)
  - Pressure (BME688)
  - Gas Resistance (BME688)
  - I2C sensor addresses detected

### Step 5: Control Devices

Use the control panel to:
- **NeoPixel LEDs**: Click LED buttons to change colors (purple by default)
- **Buzzer**: Click "Beep" to test, "Off" to stop
- **MOSFETs**: Toggle 4 MOSFET outputs on/off
- **I2C Scan**: Click to scan for connected sensors (should show BME688 addresses)

## Troubleshooting COM Ports

### If COM3, COM4, etc. are not working:

1. **Check Device Manager**:
   - Press `Win + X` → Device Manager
   - Look under "Ports (COM & LPT)"
   - Find your USB Serial devices
   - Note the COM port numbers

2. **Check if ports are in use**:
   - Close Arduino IDE, Serial Monitor, PuTTY, or any other serial tools
   - Try disconnecting and reconnecting USB cables

3. **Try different USB ports**:
   - USB-C ports may be on different controllers
   - Try front vs back USB ports

4. **Check drivers**:
   - ESP32-S3 typically uses CH340 or CP2102 drivers
   - Download from manufacturer if needed

5. **Manual port identification**:
   - Connect one USB-C at a time
   - Note which COM port appears
   - Label them as Side-A and Side-B

## Device Registration

When a device connects:
- **MAC Address**: Automatically queried and stored
- **I2C Sensors**: Automatically scanned (BME688 should appear)
- **Firmware Version**: Retrieved if available
- **Device ID**: Format: `mycobrain-side-a-COM3` or `mycobrain-side-b-COM4`

## Expected I2C Addresses

- **BME688 Sensor 1**: Typically `0x76` or `0x77`
- **BME688 Sensor 2**: Typically `0x76` or `0x77` (if different address)
- Both sensors should appear in the I2C scan if properly connected

## API Endpoints

### Service Health
```
GET http://localhost:8003/health
```

### List Devices
```
GET http://localhost:8003/devices
```

### Scan Ports
```
GET http://localhost:8003/ports
```

### Connect Device
```
POST http://localhost:8003/devices/connect/COM3
Body: {
  "side": "side-a",
  "baudrate": 115200
}
```

### Get Telemetry
```
GET http://localhost:8003/devices/{device_id}/telemetry
```

### Send Command
```
POST http://localhost:8003/devices/{device_id}/command
Body: {
  "command": {
    "command_type": "set_neopixel",
    "led_index": 0,
    "r": 255,
    "g": 0,
    "b": 255
  },
  "use_mdp": true
}
```

## Next Steps

1. **Verify both devices are connected** (Side-A and Side-B)
2. **Check telemetry is updating** (temperature, humidity, etc.)
3. **Test controls** (LEDs, buzzer, MOSFETs)
4. **Verify I2C sensors** are detected (should show BME688 addresses)
5. **Note the MAC addresses** for future device identification

## Integration with N8n

To create N8n workflows for MycoBrain:

1. **Webhook Trigger**: `http://localhost:5678/webhook/mycobrain/telemetry`
2. **HTTP Request Node**: Call MycoBrain service API
3. **Conditional Logic**: Check sensor thresholds
4. **Actions**: Send commands, log data, send alerts

Example workflow:
- Monitor temperature → If > 30°C → Turn on fan (MOSFET)
- Monitor humidity → If < 40% → Alert via notification
- Log all telemetry → Store in database every minute

## Docker Integration (Future)

For Docker deployment, the service needs:
- Serial port access (`/dev/ttyUSB0`, `/dev/ttyUSB1` on Linux)
- USB passthrough configuration
- On Windows, consider running service directly (not in Docker) for easier serial access

## Support

- **Service Logs**: Check console output from `mycobrain_dual_service.py`
- **API Docs**: http://localhost:8003/docs (FastAPI Swagger UI)
- **Device Issues**: Check serial connection, baud rate (115200), firmware compatibility

