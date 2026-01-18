# MycoBrain System Test Report
## Date: 2026-01-16 22:56:57

## Overview
All MycoBrain systems have been tested and verified working.

---

## Test Results

### Local System (Windows Development Machine)

| Component | Status | Details |
|-----------|--------|---------|
| MycoBrain Service | âœ… PASS | Running on port 8003 |
| Device Connection | âœ… PASS | COM7 (ESP32-S3) |
| BME688 Sensors | âœ… PASS | 2x detected (0x76, 0x77) |
| NeoPixel LED | âœ… PASS | Color control working |
| Buzzer | âœ… PASS | Frequency/tone working |
| Website API | âœ… PASS | localhost:3000/api/mycobrain |
| Device Manager UI | âœ… PASS | Full sensor display |

### Sandbox System (VM 192.168.0.187)

| Component | Status | Details |
|-----------|--------|---------|
| Bridge Connection | âœ… PASS | VM â†’ Windows:8003 |
| Firewall Rule | âœ… PASS | Port 8003 open |
| Website API | âœ… PASS | sandbox.mycosoft.com/api/mycobrain |
| Remote LED Control | âœ… PASS | Works via sandbox |
| Remote Buzzer | âœ… PASS | Works via sandbox |
| Live Sensor Data | âœ… PASS | Real-time streaming |

---

## Current Configuration

### Windows Machine (192.168.0.172)
- **MycoBrain Service**: Running on port 8003
- **Device**: COM7 (ESP32-S3, VID:303A PID:1001)
- **Firmware**: 2.0.0
- **Sensors**: 2x BME688 (AMB @ 0x77, ENV @ 0x76)

### VM Sandbox (192.168.0.187)
- **MYCOBRAIN_SERVICE_URL**: http://192.168.0.172:8003
- **Cloudflare Tunnel**: Active for sandbox.mycosoft.com
- **Website Container**: mycosoft-website

---

## Live Sensor Data (at time of test)

| Sensor | Temp (Â°C) | Humidity (%) | Pressure (hPa) | Gas (kÎ©) | IAQ |
|--------|-----------|--------------|----------------|----------|-----|
| ENV (0x76) | 23.4 | 36.7 | 692 | 172.0 | 50 |
| AMB (0x77) | 23.4 | 35.9 | 645 | 279.9 | 50 |

### Smell Detection
- **Classification**: Fresh Mushroom Fruiting
- **Category**: fungal (Class 0)
- **Confidence**: 65%
- **VOC Composition**:
  - 1-Octen-3-ol: 45%
  - Ethanol: 25%
  - Acetaldehyde: 15%
  - Other VOCs: 15%

---

## Commands for Future Reference

### Start MycoBrain Service (Windows)
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
python -m uvicorn services.mycobrain.mycobrain_service:app --host 0.0.0.0 --port 8003
```

### Test Service Health
```powershell
Invoke-RestMethod http://localhost:8003/health
```

### Test LED Control
```powershell
Invoke-RestMethod -Uri http://localhost:8003/devices/COM7/neopixel -Method POST -ContentType "application/json" -Body '{"r":0,"g":255,"b":0,"brightness":128,"mode":"solid"}'
```

### Test Buzzer
```powershell
Invoke-RestMethod -Uri http://localhost:8003/devices/COM7/buzzer -Method POST -ContentType "application/json" -Body '{"frequency":1000,"duration_ms":100,"pattern":"beep"}'
```

### Update VM Container
```bash
ssh mycosoft@192.168.0.187
docker exec mycosoft-website printenv | grep MYCOBRAIN
docker stop mycosoft-website && docker rm mycosoft-website
docker compose up -d mycosoft-website
```

---

## Status: âœ… ALL SYSTEMS OPERATIONAL
