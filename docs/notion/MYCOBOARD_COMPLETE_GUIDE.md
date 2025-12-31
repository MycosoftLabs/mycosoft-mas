# MycoBoard Complete Guide

> **Notion Knowledge Base Export**
> *For Mycosoft Engineering Team*

---

## Quick Reference

| Item | Value |
|------|-------|
| **Board** | ESP32-S3 (240MHz dual-core) |
| **Sensors** | 2x BME688 (0x76, 0x77) |
| **LED** | NeoPixel on GPIO 15 |
| **Buzzer** | Piezo on GPIO 46 |
| **LoRa** | SX1262 (915MHz) |
| **USB** | Native USB-CDC |
| **Baud Rate** | 115200 |
| **Service Port** | 8003 |
| **Website Port** | 3000 |

---

## Pin Assignments

### I2C Bus
- **SDA**: GPIO 5
- **SCL**: GPIO 4
- **Speed**: 100kHz

### Peripherals
| GPIO | Function |
|------|----------|
| 15 | NeoPixel Data |
| 46 | Piezo Buzzer |

### LoRa Radio (SX1262)
| GPIO | Function |
|------|----------|
| 17 | NSS (Chip Select) |
| 18 | SCK (SPI Clock) |
| 19 | MISO |
| 20 | MOSI |
| 21 | RESET |
| 47 | DIO1 (Interrupt) |
| 48 | BUSY |

---

## Firmware Commands

### System
```
help       - Show all commands
status     - Full system status
scan       - I2C bus scan
poster     - Boot screen
```

### Sensors
```
live on/off    - Enable/disable streaming
dbg on/off     - Enable/disable debug
fmt lines/json - Output format
rate amb lp    - Set AMB to low power
rate env ulp   - Set ENV to ultra low power
```

### LED Control
```
led mode off      - Turn off
led mode state    - System state
led mode manual   - Manual control
led rgb R G B     - Set color (0-255)
```

### Audio
```
coin   - Coin sound
morgio - Boot jingle
power  - Power up
1up    - 1-up sound
```

---

## API Endpoints

### MycoBrain Service (Port 8003)

```bash
# Health check
curl http://localhost:8003/health

# List ports
curl http://localhost:8003/ports

# Connect device
curl -X POST http://localhost:8003/devices/connect/ttyACM0

# List devices
curl http://localhost:8003/devices

# Send command
curl -X POST http://localhost:8003/devices/mycobrain-ttyACM0/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "status"}}'
```

### Website API (Port 3000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mycobrain` | GET | List devices |
| `/api/mycobrain/ports` | GET | List ports |
| `/api/mycobrain/{port}/sensors` | GET | Sensor data |
| `/api/mycobrain/{port}/control` | POST | Send command |
| `/api/mycobrain/{port}/diagnostics` | GET | Run diagnostics |

---

## Docker Deployment

### Start Services
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\start-all-persistent.ps1
```

### Manual Start
```bash
docker compose -f docker-compose.always-on.yml \
               -f docker-compose.always-on.hardware.yml \
               up -d
```

### USB Passthrough (Windows)
```powershell
# Install usbipd
winget install dorssel.usbipd-win

# List devices
usbipd list

# Attach to WSL
usbipd bind --busid <BUSID>
usbipd attach --wsl --busid <BUSID>

# Load driver
wsl -d docker-desktop -e modprobe cdc_acm
```

---

## Sensor Data Format

### BME688 Fields

| Field | Description | Unit |
|-------|-------------|------|
| T | Temperature | °C |
| RH | Humidity | % |
| P | Pressure | hPa |
| Gas | Gas Resistance | Ohm |
| IAQ | Air Quality Index | 0-500 |
| acc | IAQ Accuracy | 0-3 |
| CO2eq | CO2 Equivalent | ppm |
| VOC | VOC Level | ppm |

### IAQ Accuracy Levels
- **0**: Sensor stabilizing
- **1**: Low confidence
- **2**: Medium confidence
- **3**: High confidence (best)

---

## Troubleshooting

### Device Not Found
1. Check USB connection
2. Run `usbipd list`
3. Attach to WSL2
4. Check `docker logs mycobrain`

### Sensors Not Reading
1. Run `scan` command
2. Check I2C addresses (0x76, 0x77)
3. Verify pin configuration
4. Try `rate amb lp`

### LED Not Working
1. Check GPIO 15 connection
2. Try `led mode manual`
3. Set `led rgb 255 0 0`

### Service Connection Issues
1. Check `curl http://localhost:8003/health`
2. Restart container
3. Check Docker logs

---

## Dependencies

### Firmware (PlatformIO)
```ini
platform = espressif32@6.4.0
board = esp32-s3-devkitc-1
framework = arduino
lib_deps =
    boschsensortec/BSEC Software Library@^1.8.1492
    fastled/FastLED@^3.6.0
    sandeepmistry/LoRa@^0.8.0
```

### Service (Python)
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pyserial>=3.5
pydantic>=2.0.0
```

---

## Team Contacts

| Role | Name |
|------|------|
| Hardware | Alberto |
| Firmware | Garrett |
| Service/API | Chris |
| General | engineering@mycosoft.com |

---

## Related Documents

- MycoBoard Technical Reference
- System Integration Guide
- MycoBrain Service README
- MDP Protocol Specification
- MycoBoard Roadmap

---

*Last Updated: December 2024*
*Mycosoft Engineering Team*























