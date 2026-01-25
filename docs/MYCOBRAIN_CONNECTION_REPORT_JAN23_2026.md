# MycoBrain Connection Report - January 23, 2026

**Date**: January 23, 2026 @ 18:01 UTC
**Status**: **CONNECTED & WORKING**

---

## Summary

MycoBrain hardware is now fully connected from the local Windows PC (COM7) to the sandbox site (sandbox.mycosoft.com) via the VM-hosted website container.

---

## Connection Details

### Local MycoBrain Service
| Field | Value |
|-------|-------|
| **Host** | 192.168.0.172 (Local Windows PC) |
| **Port** | 8003 |
| **COM Port** | COM7 |
| **VID:PID** | 303A:1001 (Espressif ESP32-S3) |
| **Service Version** | 2.2.0 |

### Hardware Detected
| Field | Value |
|-------|-------|
| **Board** | ESP32-S3 (Mycosoft ESP32AB) |
| **Device ID** | mycobrain-COM7 |
| **BME688 Sensors** | 2 (addresses 0x77, 0x76) |
| **I2C Config** | SDA=5, SCL=4 @ 100kHz |

### Network Path
```
User Browser
    ↓ HTTPS
sandbox.mycosoft.com (Cloudflare)
    ↓ Tunnel
VM 192.168.0.187:3000 (Website Container)
    ↓ HTTP (MYCOBRAIN_SERVICE_URL)
Local PC 192.168.0.172:8003 (MycoBrain Service)
    ↓ USB Serial
ESP32-S3 on COM7
```

---

## Configuration Applied

### VM Website Container
```yaml
environment:
  MYCOBRAIN_SERVICE_URL: http://192.168.0.172:8003
```

### Files Updated
1. `/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml` - Updated MYCOBRAIN_SERVICE_URL
2. Website container recreated with new environment variable

---

## API Endpoints Working

| Endpoint | Status | Response |
|----------|--------|----------|
| `/api/mycobrain/health` | ✓ PASS | `{"status":"ok","devices_connected":1,"serviceUrl":"http://192.168.0.172:8003"}` |
| `/api/mycobrain/devices` | ✓ PASS | Shows mycobrain-COM7 with ESP32-S3 board, 2 BME688 sensors |
| `/api/mycobrain/ports` | ✓ PASS | Lists available COM ports |

### Verified Working Data

```json
{
  "device_id": "mycobrain-COM7",
  "port": "COM7",
  "status": "connected",
  "info": {
    "board": "ESP32-S3",
    "raw_status": "BME688 count: 2 | MycoBrain DeviceManager + BSEC2 | Mycosoft ESP32AB"
  },
  "protocol": "MDP v1"
}
```

---

## Sensor Status

The BME688 sensors are detected but showing subscription failures:
- **AMB (0x77)**: Initialized OK, subscription FAILED
- **ENV (0x76)**: Initialized OK, subscription FAILED

This may indicate:
1. BSEC2 library initialization needed
2. Sensor configuration required
3. Firmware may need update for full BSEC2 support

---

## Keeping It Running

### On Windows PC (Required)
The MycoBrain service must keep running for the sandbox to access the device:

```powershell
# Current process running MycoBrain
# If it stops, restart with:
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python services\mycobrain\mycobrain_service_standalone.py
```

### Auto-Start Option (RECOMMENDED)
To have MycoBrain start automatically on Windows boot:

**Option 1: Windows Task Scheduler (Recommended)**
```powershell
# Run as Administrator
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\install-mycobrain-autostart.ps1
```

This creates a scheduled task that:
- Starts MycoBrain service 60 seconds after Windows boot (waits for USB/COM ports)
- Also starts on user logon (backup trigger)
- Automatically restarts if service fails (up to 3 times)
- Logs to `logs\mycobrain-service.log`

**To verify task is installed:**
```powershell
Get-ScheduledTask -TaskName "MycoBrain-Service-AutoStart" | Format-List
```

**To test without restarting:**
```powershell
Start-ScheduledTask -TaskName "MycoBrain-Service-AutoStart"
```

**To remove the task:**
```powershell
.\scripts\install-mycobrain-autostart.ps1 -Remove
```

**Option 2: Windows Service (Alternative)**
Use NSSM (Non-Sucking Service Manager) to run as a Windows Service

---

## Troubleshooting

### If sandbox shows "unhealthy" or 503:
1. Check if MycoBrain service is running locally: `curl http://localhost:8003/health`
2. Check if COM7 is available: `[System.IO.Ports.SerialPort]::GetPortNames()`
3. Reconnect if needed: `curl -X POST "http://localhost:8003/devices/connect/COM7?baudrate=115200"`

### If device disconnects:
```powershell
# Reconnect to COM7
curl.exe -X POST "http://localhost:8003/devices/connect/COM7?baudrate=115200"
```

---

## Next Steps

1. [x] Set up Windows auto-start for MycoBrain service - **Script created: `scripts/install-mycobrain-autostart.ps1`**
2. [ ] Investigate BME688 subscription failures - **See: `docs/BME688_SUBSCRIPTION_FAILURE_INVESTIGATION.md`**
3. [ ] Consider adding Supabase webhook callbacks for real-time data
4. [x] Update `/myca` redirect in website - **Already implemented in next.config.js**

---

**Connection Verified**: ✓ PASS
**Timestamp**: 2026-01-23T18:01:47 UTC
