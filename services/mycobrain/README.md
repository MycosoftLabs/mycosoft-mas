# MycoBrain Service

> **Real-time hardware communication service for MycoBoard devices**

The MycoBrain service is a FastAPI-based Python service that provides a REST API for communicating with MycoBoard ESP32-S3 hardware devices over USB serial connections.

## Features

- 🔌 **Automatic Device Detection**: Discovers MycoBoard devices on serial ports
- 📡 **Real-time Communication**: Bidirectional serial communication with hardware
- 🌡️ **Sensor Data Streaming**: Live environmental sensor data (BME688)
- 💡 **Peripheral Control**: LED colors, buzzer sounds, and more
- 🔧 **Diagnostics**: I2C bus scanning, board identification
- 🐳 **Docker Ready**: Full containerization with USB passthrough support

## Quick Start

### Local Development

```bash
cd services/mycobrain

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run service
python mycobrain_service_standalone.py
```

The service will start on `http://localhost:8003`.

### Docker Deployment

```bash
# From project root
docker compose -f docker-compose.always-on.yml \
               -f docker-compose.always-on.hardware.yml \
               up -d mycobrain
```

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/ports` | GET | List available serial ports |
| `/devices` | GET | List connected devices |

### Device Connection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices/connect/{port}` | POST | Connect to device on port |
| `/devices/{device_id}/disconnect` | POST | Disconnect device |

### Commands

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices/{device_id}/command` | POST | Send command to device |

**Example Request:**
```json
POST /devices/mycobrain-ttyACM0/command
{
  "command": {
    "cmd": "led rgb 255 0 0"
  }
}
```

## Device ID Format

Device IDs follow the pattern: `mycobrain-{port_name}`

Examples:
- Linux/Docker: `mycobrain-ttyACM0`
- Windows: `mycobrain-COM5`

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MYCOBRAIN_HOST` | `0.0.0.0` | Service bind address |
| `MYCOBRAIN_PORT` | `8003` | Service port |
| `DEFAULT_SERIAL_PORT` | `/dev/ttyACM0` | Default serial port |
| `DEFAULT_BAUDRATE` | `115200` | Serial baud rate |

## USB Passthrough (Windows + WSL2)

For Docker on Windows, use `usbipd-win` for USB passthrough:

```powershell
# Install usbipd-win
winget install dorssel.usbipd-win

# List USB devices
usbipd list

# Bind and attach MycoBoard (adjust busid as needed)
usbipd bind --busid 13-3
usbipd attach --wsl --busid 13-3

# Load CDC driver in WSL2
wsl -d docker-desktop -e modprobe cdc_acm
```

The device will appear as `/dev/ttyACM0` inside Docker containers.

## Dependencies

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pyserial>=3.5
pydantic>=2.0.0
python-multipart>=0.0.6
httpx>=0.26.0
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MycoBrain Service                         │
│                     (Port 8003)                              │
├─────────────────────────────────────────────────────────────┤
│  FastAPI REST API                                            │
│  ├── /health, /ports, /devices                              │
│  ├── /devices/connect/{port}                                │
│  └── /devices/{device_id}/command                           │
├─────────────────────────────────────────────────────────────┤
│  Serial Manager                                              │
│  ├── Auto-discovery of serial ports                         │
│  ├── Connection pooling                                      │
│  └── Thread-safe read/write                                 │
├─────────────────────────────────────────────────────────────┤
│  USB Serial                                                  │
│  └── /dev/ttyACM0 (Linux) or COM5 (Windows)                 │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                     MycoBoard                                │
│                   (ESP32-S3)                                 │
├─────────────────────────────────────────────────────────────┤
│  ├── BME688 x2 (Environmental Sensors)                      │
│  ├── NeoPixel LED (GPIO 15)                                 │
│  ├── Piezo Buzzer (GPIO 46)                                 │
│  └── LoRa Radio (SX1262)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Integration with Website

The Mycosoft website (`mycosoft-website`) communicates with this service via internal Docker networking:

```
Website (Next.js)
    │
    ▼ /api/mycobrain/*
    │
    ├── /api/mycobrain/ports → GET http://mycobrain:8003/ports
    ├── /api/mycobrain/{port}/sensors → POST .../command (status)
    ├── /api/mycobrain/{port}/control → POST .../command
    └── /api/mycobrain/{port}/diagnostics → Multiple API calls
```

## Related Documentation

- [MycoBoard Technical Reference](../../docs/MYCOBOARD_TECHNICAL_REFERENCE.md)
- [System Integration Guide](../../docs/SYSTEM_INTEGRATION_GUIDE.md)
- [MDP Protocol Spec](../../docs/protocols/MDP_V1_SPEC.md)

## Contact

- **Service Issues:** Chris
- **Hardware Issues:** Alberto
- **Firmware Issues:** Garrett

---

*Part of the Mycosoft Multi-Agent System (MAS)*
