# MycoBoard Technical Reference

> **For: Garrett, Chris, Alberto, and all Mycosoft engineering staff**
> **Last Updated:** December 2024
> **Status:** Production-Ready

## Overview

The **MycoBoard** is Mycosoft's custom ESP32-S3-based environmental monitoring and control board. It features dual BME688 environmental sensors, LoRa radio for long-range mesh communication, NeoPixel LEDs, and a piezo buzzer for audio feedback.

## Hardware Specifications

### Core MCU
- **Chip:** ESP32-S3 (Xtensa LX7 dual-core @ 240MHz)
- **Flash:** 16MB
- **RAM:** 8MB PSRAM
- **USB:** Native USB-CDC (no FTDI required)

### Pin Configuration

| Pin | Function | Notes |
|-----|----------|-------|
| GPIO 4 | I2C SCL | Shared I2C bus clock |
| GPIO 5 | I2C SDA | Shared I2C bus data |
| GPIO 15 | NeoPixel Data | FastLED, WS2812B-compatible |
| GPIO 46 | Piezo Buzzer | PWM audio output |
| GPIO 17 | LoRa NSS | SX1262 chip select |
| GPIO 18 | LoRa SCK | SPI clock |
| GPIO 19 | LoRa MISO | SPI data in |
| GPIO 20 | LoRa MOSI | SPI data out |
| GPIO 21 | LoRa RESET | Module reset |
| GPIO 47 | LoRa DIO1 | Interrupt |
| GPIO 48 | LoRa BUSY | Busy signal |

### I2C Devices (Default Bus @ 100kHz)

| Address | Device | Description |
|---------|--------|-------------|
| 0x76 | BME688 #2 | ENV sensor (environment enclosure) |
| 0x77 | BME688 #1 | AMB sensor (ambient/ambient) |

### BME688 Sensor Capabilities
- Temperature: -40°C to +85°C (±0.5°C accuracy)
- Humidity: 0-100% RH (±3% accuracy)
- Pressure: 300-1100 hPa (±1 hPa accuracy)
- Gas: VOC detection, IAQ index calculation
- IAQ Accuracy: 0=unstable, 1=low, 2=medium, 3=high

## Firmware CLI Commands

The MycoBoard firmware exposes a serial CLI over USB-CDC (115200 baud). Commands are newline-terminated.

### Core Commands

| Command | Description | Example Response |
|---------|-------------|------------------|
| `help` | List all commands | Command list |
| `status` | Full system status | Core version, sensors, LED state |
| `scan` | I2C bus scan | `found: 0x76`, `found: 0x77` |
| `poster` | Reprint boot screen | ASCII art |

### Sensor Commands

| Command | Description |
|---------|-------------|
| `live on` | Enable periodic sensor output |
| `live off` | Disable periodic output |
| `dbg on` | Enable debug prints |
| `dbg off` | Disable debug prints |
| `fmt lines` | Human-readable output |
| `fmt json` | NDJSON output format |
| `rate amb lp` | Set AMB sensor to low-power mode |
| `rate env ulp` | Set ENV sensor to ultra-low-power |
| `probe amb 3` | Read AMB chip_id 3 times |
| `regs env` | Read ENV registers once |

### LED Commands

| Command | Description |
|---------|-------------|
| `led mode off` | Turn off LED |
| `led mode state` | LED reflects system state |
| `led mode manual` | Manual RGB control |
| `led rgb 255 0 0` | Set to red (R G B values 0-255) |
| `led rgb 0 255 0` | Set to green |
| `led rgb 0 0 255` | Set to blue |

### Audio Commands

| Command | Description |
|---------|-------------|
| `coin` | Play coin/bump sound effect |
| `morgio` | Play SuperMorgIO boot jingle |
| `bump` | Alias for coin |
| `power` | Power-up sound |
| `1up` | 1-up sound |

### I2C Commands

| Command | Description |
|---------|-------------|
| `i2c 5 4 100000` | Set I2C to SDA=5, SCL=4, 100kHz |

## API Integration

### MycoBrain Service (Port 8003)

The MycoBrain service provides a REST API to control the board:

```bash
# Health check
curl http://localhost:8003/health

# List available ports
curl http://localhost:8003/ports

# Connect to device
curl -X POST http://localhost:8003/devices/connect/ttyACM0

# List connected devices
curl http://localhost:8003/devices

# Send command
curl -X POST http://localhost:8003/devices/mycobrain-ttyACM0/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "status"}}'

# Control LED
curl -X POST http://localhost:8003/devices/mycobrain-ttyACM0/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "led rgb 255 0 255"}}'
```

### Website API Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mycobrain` | GET | List devices |
| `/api/mycobrain/ports` | GET | List serial ports |
| `/api/mycobrain/{port}/sensors` | GET | Get sensor data |
| `/api/mycobrain/{port}/control` | POST | Send control command |
| `/api/mycobrain/{port}/diagnostics` | GET | Run diagnostics |

## Docker Deployment

### USB Passthrough (Windows + WSL2)

The MycoBoard uses USB-CDC which requires `usbipd-win` for Docker access:

```powershell
# Install usbipd-win
winget install dorssel.usbipd-win

# List USB devices
usbipd list

# Bind and attach to WSL
usbipd bind --busid 13-3
usbipd attach --wsl --busid 13-3

# Load CDC driver in WSL
wsl -d docker-desktop -e modprobe cdc_acm
```

The device appears as `/dev/ttyACM0` in the Linux Docker container.

### Docker Compose

```yaml
# docker-compose.always-on.hardware.yml
services:
  mycobrain:
    privileged: true
    devices:
      - "/dev/ttyACM0:/dev/ttyACM0"
    environment:
      - DEFAULT_SERIAL_PORT=/dev/ttyACM0
```

## Development Setup

### Required Dependencies (Firmware)

```ini
# platformio.ini
[env:esp32-s3]
platform = espressif32@6.4.0
board = esp32-s3-devkitc-1
framework = arduino
lib_deps =
    boschsensortec/BSEC Software Library@^1.8.1492
    fastled/FastLED@^3.6.0
    sandeepmistry/LoRa@^0.8.0
```

### Required Dependencies (Service)

```txt
# requirements.txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pyserial>=3.5
```

## Sensor Data Format

### Status Response Example

```
--- CORE / SDK ---
Arduino-ESP32 core: 3.3.5
ESP SDK: v5.5.1-931-g9bb7aa84fe
Chip model: ESP32-S3
CPU freq: 240 MHz
---------------
I2C: SDA=5 SCL=4 @ 100000 Hz
Format=lines Debug=on Live=on period=1000ms
LED mode=manual  manual rgb=0,255,0
AMB: present=YES addr=0x77 begin=OK sub=FAIL status=14 rate=LP
ENV: present=YES addr=0x76 begin=OK sub=FAIL status=14 rate=LP
AMB addr=0x77 age=2630ms T=20.41C RH=42.13% P=705.61hPa Gas=37026Ohm IAQ=72.41 acc=1 CO2eq=597.89 VOC=0.62
ENV addr=0x76 age=2572ms T=21.16C RH=36.32% P=642.76hPa Gas=67493Ohm IAQ=79.04 acc=3 CO2eq=739.11 VOC=0.86
```

### Parsed Sensor Fields

| Field | Description | Unit |
|-------|-------------|------|
| T | Temperature | °C |
| RH | Relative Humidity | % |
| P | Pressure | hPa |
| Gas | Gas Resistance | Ohm |
| IAQ | Indoor Air Quality Index | 0-500 |
| acc | IAQ Accuracy | 0-3 |
| CO2eq | CO2 Equivalent | ppm |
| VOC | Volatile Organic Compounds | ppm |

## Communication Protocols

### LoRa (Side-A ↔ Side-B)

The MycoBoard supports LoRa communication for mesh networking:

- **Frequency:** 915 MHz (US) / 868 MHz (EU)
- **Spreading Factor:** SF7-SF12
- **Bandwidth:** 125 kHz / 250 kHz / 500 kHz
- **TX Power:** Up to 20 dBm

### ESP-NOW Mesh

For local mesh networking without WiFi infrastructure:

- **Protocol:** ESP-NOW (proprietary Espressif)
- **Range:** ~200m line of sight
- **Latency:** <10ms
- **Max Nodes:** 20 peers

## Troubleshooting

### Device Not Detected

1. Check USB connection
2. Verify driver installation (Windows: `usbipd list`)
3. Check container privileges (`privileged: true`)
4. Verify port mapping in Docker Compose

### Sensors Not Reading

1. Run `scan` to verify I2C devices
2. Check `status` for sensor initialization
3. Ensure I2C pins (SDA=5, SCL=4) are correct
4. Try `rate amb lp` to reinitialize

### LED Not Working

1. Verify GPIO 15 is connected to NeoPixel data
2. Try `led mode manual` then `led rgb 255 0 0`
3. Check power supply (3.3V or 5V depending on LED strip)

### Service Connection Issues

1. Check service is running: `curl http://localhost:8003/health`
2. Verify port is not locked: `/api/mycobrain/ports/clear-locks`
3. Restart MycoBrain container

## Board Identification

The diagnostics endpoint can identify board type:

| Marker | Board Type |
|--------|------------|
| `SuperMorgIO` | MycoBoard |
| `AMB addr=0x77` | MycoBoard |
| `ENV addr=0x76` | MycoBoard |
| `ESP32-S3` (no markers) | Generic ESP32-S3 |

## Standards & Best Practices

1. **Always use device_id** (e.g., `mycobrain-ttyACM0`) instead of raw port paths
2. **Timeout all API calls** (5-8 seconds for commands)
3. **Log diagnostics to MINDEX** for MYCA learning
4. **Use `fmt json`** for automated parsing
5. **Check IAQ accuracy** before trusting IAQ values (acc=3 is best)

## Contact

- **Hardware Issues:** Alberto
- **Firmware Issues:** Garrett
- **Service/API Issues:** Chris
- **General Questions:** engineering@mycosoft.com

---

*This document is auto-generated from the working MycoBoard configuration as of December 2024.*

