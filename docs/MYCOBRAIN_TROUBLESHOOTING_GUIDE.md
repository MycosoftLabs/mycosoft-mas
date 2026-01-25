# MycoBrain Troubleshooting Guide

**Version**: 1.0  
**Last Updated**: January 20, 2026  
**Audience**: Developers, DevOps, Support Staff

---

## Quick Diagnostics

### Is MycoBrain Service Running?

```powershell
# Check health endpoint
(Invoke-WebRequest -Uri "http://localhost:8003/health" -TimeoutSec 5).Content
```

**Expected Output**:
```json
{"status":"healthy","devices_connected":1,"ports_available":5}
```

### Is Device Connected?

```powershell
# List connected devices
(Invoke-WebRequest -Uri "http://localhost:8003/devices" -TimeoutSec 5).Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

**Expected**: See device on COM7 with recent `last_message_time`

---

## Common Issues & Solutions

### Issue 1: Controls Show in UI But Don't Affect Device

**Symptoms**:
- LED/Buzzer buttons visible
- Clicking them shows "success" but device doesn't respond
- Sensor data is stale (hours old)

**Cause**: Another process is holding the serial port

**Diagnosis**:
```powershell
# Check for duplicate MycoBrain services
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | 
    Where-Object { $_.CommandLine -match "mycobrain|uvicorn" } | 
    Select-Object ProcessId, CommandLine | Format-List

# Check what's listening on MycoBrain ports
netstat -ano | findstr ":8003 :18003"
```

**Solution**:
```powershell
# 1. Kill the duplicate service (replace PID with actual)
Stop-Process -Id <DUPLICATE_PID> -Force

# 2. Disconnect from device
Invoke-WebRequest -Uri "http://localhost:8003/devices/disconnect/COM7" -Method POST

# 3. Wait for port release
Start-Sleep -Seconds 3

# 4. Reconnect
Invoke-WebRequest -Uri "http://localhost:8003/devices/connect/COM7" -Method POST
```

---

### Issue 2: "Port COM7 in use by another application"

**Symptoms**:
- Connection attempt fails
- Error message mentions port in use

**Cause**: Another application has the serial port open

**Diagnosis**:
```powershell
# List COM ports
python -c "import serial.tools.list_ports; [print(f'{p.device}: {p.description}') for p in list(serial.tools.list_ports.comports())]"
```

**Common Port Hogs**:
- Arduino IDE Serial Monitor
- PuTTY or other serial terminals
- Previous Python process that crashed
- Duplicate MycoBrain service

**Solution**:
1. Close Arduino IDE / Serial monitors
2. Kill stale Python processes:
   ```powershell
   Get-Process python* | Stop-Process -Force
   ```
3. Restart MycoBrain service

---

### Issue 3: Service Won't Start - "Address Already in Use"

**Symptoms**:
- Error: `[Errno 10048] error while attempting to bind on address`
- Service fails to start on port 8003

**Diagnosis**:
```powershell
# Find what's using port 8003
$pid = (Get-NetTCPConnection -LocalPort 8003 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($pid) { Get-Process -Id $pid } else { Write-Host "Port 8003 is free" }
```

**Solution**:
```powershell
# Kill process on port 8003
$pid = (Get-NetTCPConnection -LocalPort 8003 -State Listen).OwningProcess
taskkill /PID $pid /F

# Wait for port to clear
Start-Sleep -Seconds 3

# Then start service
```

---

### Issue 4: Device Shows Connected But Telemetry Frozen

**Symptoms**:
- `/devices` shows `connected: true`
- `last_message_time` is hours old
- Sensor values don't update

**Cause**: Serial communication is blocked or device is hung

**Solution A - Reconnect**:
```powershell
# Disconnect
Invoke-WebRequest -Uri "http://localhost:8003/devices/disconnect/COM7" -Method POST
Start-Sleep -Seconds 2

# Reconnect
Invoke-WebRequest -Uri "http://localhost:8003/devices/connect/COM7" -Method POST
```

**Solution B - Power Cycle Device**:
1. Unplug USB cable from MycoBrain
2. Wait 5 seconds
3. Reconnect USB cable
4. Wait for device to boot (LED will flash)
5. Connect via API:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8003/devices/connect/COM7" -Method POST
   ```

---

### Issue 5: Wrong Device ID in API Calls

**Symptoms**:
- 404 Not Found on device commands
- Logs show: `Device not found: mycobrain-XX:XX:XX...`

**Cause**: Device ID format mismatch

**Correct Format**:
```
mycobrain-{MAC_ADDRESS}
Example: mycobrain-10:B4:1D:E3:3B:C4
```

**Get Correct Device ID**:
```powershell
$devices = (Invoke-WebRequest -Uri "http://localhost:8003/devices").Content | ConvertFrom-Json
$devices.devices | ForEach-Object { Write-Host "Port: $($_.port) -> ID: $($_.sensor_data.node)" }
```

---

### Issue 6: BME688 Sensors Not Detected

**Symptoms**:
- `bme688_count: 0` in telemetry
- Peripheral scan shows no I2C devices

**Diagnosis**:
```powershell
$body = @{command=@{cmd="sensors"}} | ConvertTo-Json -Depth 3
$response = Invoke-WebRequest -Uri "http://localhost:8003/devices/COM7/command" -Method POST -Body $body -ContentType "application/json"
$response.Content | ConvertFrom-Json
```

**Possible Causes**:
1. I2C wires disconnected
2. Wrong I2C address configured
3. BSEC library not initialized

**Solution**:
1. Check physical connections
2. Run I2C scan on device:
   ```powershell
   $body = @{command=@{cmd="i2c 5 4"}} | ConvertTo-Json -Depth 3
   Invoke-WebRequest -Uri "http://localhost:8003/devices/COM7/command" -Method POST -Body $body -ContentType "application/json"
   ```
3. If sensors still not found, reflash firmware

---

## Service Management

### Start MycoBrain Service

```powershell
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\services\mycobrain"

# Set environment
$env:MINDEX_API_URL = "http://192.168.0.187:8000"
$env:MINDEX_API_KEY = "local-dev-key"
$env:MYCOBRAIN_PUSH_TELEMETRY_TO_MINDEX = "true"

# Start (foreground)
python -m uvicorn mycobrain_service:app --host 0.0.0.0 --port 8003

# OR start in background
Start-Process python -ArgumentList "-m uvicorn mycobrain_service:app --host 0.0.0.0 --port 8003"
```

### Stop MycoBrain Service

```powershell
# Find and kill
$pid = (Get-NetTCPConnection -LocalPort 8003 -State Listen).OwningProcess
Stop-Process -Id $pid -Force
```

### Restart MycoBrain Service

```powershell
# Stop
$pid = (Get-NetTCPConnection -LocalPort 8003 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($pid) { Stop-Process -Id $pid -Force }
Start-Sleep -Seconds 2

# Start
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\services\mycobrain"
$env:MINDEX_API_URL = "http://192.168.0.187:8000"
$env:MINDEX_API_KEY = "local-dev-key"
Start-Process python -ArgumentList "-m uvicorn mycobrain_service:app --host 0.0.0.0 --port 8003"
```

---

## API Reference

### Health Check
```
GET http://localhost:8003/health
```

### List Available Ports
```
GET http://localhost:8003/ports
```

### Connect to Device
```
POST http://localhost:8003/devices/connect/{port}
Example: POST http://localhost:8003/devices/connect/COM7
```

### Disconnect Device
```
POST http://localhost:8003/devices/disconnect/{port}
```

### Get Device Status
```
GET http://localhost:8003/devices/{port}/status
```

### Send Command
```
POST http://localhost:8003/devices/{port}/command
Body: {"command": {"cmd": "sensors"}}
```

### Control NeoPixel LED
```
POST http://localhost:8003/devices/{port}/neopixel
Body: {"r": 255, "g": 0, "b": 0, "mode": "solid"}
Modes: solid, pulse, breathe, off
```

### Control Buzzer
```
POST http://localhost:8003/devices/{port}/buzzer
Body: {"sound": "coin"}
Sounds: coin, beep, alert, startup
```

---

## Hardware Reference

### MycoBrain ESP32-S3 Pins

| Function | GPIO |
|----------|------|
| NeoPixel LED | GPIO15 |
| Buzzer | GPIO16 |
| I2C SDA | GPIO5 |
| I2C SCL | GPIO4 |

### BME688 I2C Addresses

| Sensor | Address |
|--------|---------|
| AMB (Ambient) | 0x77 |
| ENV (Environment) | 0x76 |

---

## Logs & Debugging

### View Service Logs

The uvicorn service outputs to console. If running in background, redirect to file:

```powershell
Start-Process python -ArgumentList "-m uvicorn mycobrain_service:app --host 0.0.0.0 --port 8003" -RedirectStandardOutput "C:\temp\mycobrain.log" -RedirectStandardError "C:\temp\mycobrain-error.log"
```

### Enable Debug Mode

```powershell
$env:DEBUG = "true"
python -m uvicorn mycobrain_service:app --host 0.0.0.0 --port 8003 --log-level debug
```

---

## Escalation Path

1. **Self-service**: Use this guide
2. **Dev team**: #dev-support channel
3. **Hardware issues**: Check physical connections, power cycle device
4. **Firmware issues**: Reflash using Arduino IDE

---

*Document Version: 1.0*  
*Created: January 20, 2026*  
*Maintainer: Mycosoft Development Team*
