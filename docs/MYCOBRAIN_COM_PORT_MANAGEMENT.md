# MycoBrain COM Port & Service Management

**Version**: 1.0.0  
**Date**: 2026-01-10  
**Status**: Active  

---

## Overview

MycoBrain devices connect via USB-C to COM ports. This document outlines procedures for managing COM port conflicts between development, testing, and production environments.

---

## Problem Statement

When developing firmware and running the MycoBrain service simultaneously:
1. Arduino IDE locks COM port during flashing
2. MycoBrain service locks COM port for telemetry
3. Both cannot access the same port simultaneously
4. Service restart required after firmware updates

---

## COM Port Architecture

### Standard Port Assignments

| COM Port | Device | Usage |
|----------|--------|-------|
| COM3-COM6 | MycoBrain Side-A | Sensor MCU (UART0) |
| COM7-COM10 | MycoBrain Side-B | Router MCU (UART2) |

### USB-C Mapping

```
MycoBrain Board
├── USB-C Port 1 (UART0) → Side-A Sensor MCU
│   └── Windows: COMx
│   └── Linux: /dev/ttyUSB0 or /dev/ttyACM0
│
└── USB-C Port 2 (UART2) → Side-B Router MCU
    └── Windows: COMy
    └── Linux: /dev/ttyUSB1 or /dev/ttyACM1
```

---

## Development Mode Procedures

### Before Flashing Firmware

1. **Stop MycoBrain Service**
```powershell
# Find and kill the mycobrain service
Get-Process -Name python | Where-Object { $_.CommandLine -like "*mycobrain*" } | Stop-Process -Force

# Or via Docker
docker stop mycosoft-always-on-mycobrain-1
```

2. **Verify COM Port is Released**
```powershell
# Check for processes using COM ports
netstat -ano | Select-String "COM"

# Or use Device Manager to see port status
devmgmt.msc
```

3. **Flash Firmware**
```powershell
# Use Arduino IDE or ESP-IDF
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_SideA
# Upload via Arduino IDE with correct COM port selected
```

4. **Restart MycoBrain Service**
```powershell
# Restart Docker container
docker start mycosoft-always-on-mycobrain-1

# Or start manually
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python -m uvicorn minimal_mycobrain:app --host 0.0.0.0 --port 8003
```

---

## Service Management

### MycoBrain Service Configuration

```yaml
# docker-compose service definition
mycobrain:
  image: mycosoft-mycobrain:latest
  container_name: mycosoft-mycobrain
  restart: unless-stopped
  ports:
    - "8003:8003"
  devices:
    - /dev/ttyUSB0:/dev/ttyUSB0
    - /dev/ttyUSB1:/dev/ttyUSB1
  environment:
    - MYCOBRAIN_PORT=COM3
    - MYCOBRAIN_BAUD=115200
```

### Graceful Service Shutdown

```python
# In the mycobrain service code
import signal
import sys

def graceful_shutdown(signum, frame):
    """Release COM port before shutdown"""
    if serial_connection:
        serial_connection.close()
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)
```

---

## Device Hot-Plug Handling

### Windows USB Detection

```powershell
# Monitor USB device events
$query = "SELECT * FROM Win32_DeviceChangeEvent WHERE EventType = 2"
Register-WMIEvent -Query $query -Action {
    Write-Host "USB device connected"
    # Trigger device discovery
    Invoke-RestMethod -Uri "http://localhost:8003/api/devices/scan" -Method POST
}
```

### Automatic COM Port Discovery

```python
# scan_ports.py
import serial.tools.list_ports

def find_mycobrain_devices():
    """Find all MycoBrain devices on COM ports"""
    devices = []
    for port in serial.tools.list_ports.comports():
        if "USB" in port.description or "Silicon Labs" in port.description:
            # Try to identify MycoBrain
            try:
                ser = serial.Serial(port.device, 115200, timeout=1)
                ser.write(b"IDENT\n")
                response = ser.readline()
                if b"MYCOBRAIN" in response:
                    devices.append({
                        "port": port.device,
                        "description": port.description,
                        "hwid": port.hwid
                    })
                ser.close()
            except:
                pass
    return devices
```

---

## Production Resilience

### Service Watchdog

```python
# watchdog.py - Runs on Proxmox or host machine
import time
import subprocess
import requests

HEALTH_CHECK_INTERVAL = 60  # seconds
MYCOBRAIN_URL = "http://localhost:8003/health"
MAX_FAILURES = 3

def check_health():
    try:
        response = requests.get(MYCOBRAIN_URL, timeout=5)
        return response.status_code == 200
    except:
        return False

def restart_service():
    subprocess.run(["docker", "restart", "mycosoft-mycobrain"])

if __name__ == "__main__":
    failure_count = 0
    while True:
        if check_health():
            failure_count = 0
        else:
            failure_count += 1
            if failure_count >= MAX_FAILURES:
                restart_service()
                failure_count = 0
        time.sleep(HEALTH_CHECK_INTERVAL)
```

### Graceful COM Port Release

The service should:
1. Detect when COM port becomes unavailable
2. Release the port lock gracefully
3. Attempt reconnection with exponential backoff
4. Notify MINDEX of device state change

```python
# Reconnection logic
class COMPortManager:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.connection = None
        self.reconnect_attempts = 0
        self.max_reconnect_delay = 60
    
    def connect(self):
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.reconnect_attempts = 0
            return True
        except serial.SerialException as e:
            self.reconnect_attempts += 1
            delay = min(2 ** self.reconnect_attempts, self.max_reconnect_delay)
            time.sleep(delay)
            return False
    
    def release(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
        self.connection = None
```

---

## Device Registration

### New Device Flow

1. Device connected to USB
2. Service discovers new COM port
3. Device sends identity beacon
4. Service registers device with MINDEX
5. Device appears in NatureOS dashboard

### MAC Address Registration

```python
# Register device MAC with MINDEX
async def register_device(mac_address: str, device_type: str):
    await mindex_client.post("/api/mindex/mycobrain/devices", json={
        "mac_address": mac_address,
        "device_type": device_type,
        "firmware_version": "1.0.0",
        "first_seen": datetime.utcnow().isoformat(),
        "status": "online"
    })
```

---

## Troubleshooting

### COM Port Locked

```powershell
# Find process using COM port
$process = Get-Process | Where-Object { $_.Modules.FileName -like "*serial*" }
Stop-Process -Id $process.Id -Force

# Or reset USB controller
pnputil /scan-devices
```

### Device Not Detected

1. Check USB cable connection
2. Verify drivers installed (CP210x for Silicon Labs)
3. Check Device Manager for yellow triangles
4. Try different USB port
5. Reset ESP32-S3 (hold BOOT + press RESET)

### Service Won't Start

1. Check if another process has COM port
2. Verify environment variables
3. Check Docker logs: `docker logs mycosoft-mycobrain`
4. Restart Docker: `docker restart mycosoft-mycobrain`

---

## Proxmox USB Passthrough

For production deployment on Proxmox:

```bash
# Identify USB device
lsusb | grep -i "Silicon Labs"

# Add USB passthrough to VM
qm set 104 -usb0 host=10c4:ea60
```

### Dynamic USB Passthrough

```bash
# Create udev rule for automatic passthrough
cat << 'EOF' > /etc/udev/rules.d/99-mycobrain.rules
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="ea60", RUN+="/usr/bin/mycobrain-attach.sh %k"
EOF
```

---

## Related Documents

- [MycoBrain Hardware Config](./MYCOBRAIN_HARDWARE_CONFIG.md)
- [Proxmox Deployment](./PROXMOX_DEPLOYMENT.md)
- [Device Manager Integration](./MYCOBRAIN_DEVICE_MANAGER_MACHINE_MODE_INTEGRATION.md)

---

*Last Updated: 2026-01-10*
