# Mycosoft System Integration Guide

> **How MycoBoard, MycoBrain, MINDEX, NatureOS, and MAS Work Together**

This document explains how all Mycosoft systems integrate to provide a complete IoT platform for environmental monitoring and control.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MYCOSOFT ECOSYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   MycoBoard │    │  MycoBrain  │    │   Website   │    │    MINDEX   │  │
│  │  (Hardware) │◄──►│  (Service)  │◄──►│  (Next.js)  │◄──►│  (FastAPI)  │  │
│  │   ESP32-S3  │    │  Port 8003  │    │  Port 3000  │    │  Port 8000  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │                  │         │
│         │                  │                  │                  │         │
│         ▼                  ▼                  ▼                  ▼         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         Docker Network                              │  │
│  │                    (mycosoft-always-on)                             │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### 1. MycoBoard (Hardware)

**What it is:** Custom ESP32-S3 development board with environmental sensors.

**Key Features:**
- Dual BME688 sensors (temperature, humidity, pressure, air quality)
- NeoPixel RGB LED for visual feedback
- Piezo buzzer for audio feedback
- LoRa radio for long-range mesh networking
- USB-CDC for serial communication

**Communication:**
- USB serial @ 115200 baud
- Text-based CLI commands (newline-terminated)
- Responds with sensor data or status messages

### 2. MycoBrain Service (Python/FastAPI)

**What it is:** Bridge service between hardware and web applications.

**Key Features:**
- Manages serial port connections
- Provides REST API for device control
- Handles command serialization/deserialization
- Supports multiple simultaneous devices

**Port:** 8003

**API Endpoints:**
```
GET  /health              → Service status
GET  /ports               → Available serial ports
GET  /devices             → Connected devices
POST /devices/connect/{port}  → Connect to device
POST /devices/{id}/command    → Send command
```

### 3. Website (Next.js)

**What it is:** Web-based user interface for the entire Mycosoft platform.

**Key Features:**
- Device Manager dashboard (NatureOS)
- Real-time sensor data visualization
- LED and buzzer controls
- Diagnostics and system health
- Integration with all backend services

**Port:** 3000

**API Routes (Next.js):**
```
/api/mycobrain           → Device list proxy
/api/mycobrain/ports     → Port list proxy
/api/mycobrain/{port}/sensors     → Sensor data
/api/mycobrain/{port}/control     → Send commands
/api/mycobrain/{port}/diagnostics → Run diagnostics
```

### 4. MINDEX (Python/FastAPI)

**What it is:** Centralized knowledge and data indexing service.

**Key Features:**
- Stores telemetry data from devices
- Provides search and retrieval APIs
- Feeds data to MYCA (AI assistant)
- Syncs with NAS storage

**Port:** 8000

**Integration Points:**
- Receives diagnostics logs from Device Manager
- Stores sensor history for analytics
- Powers AI-based insights and recommendations

## Data Flow

### Sensor Data Flow

```
MycoBoard                MycoBrain              Website                MINDEX
    │                        │                     │                     │
    │ [Serial: "status"]     │                     │                     │
    │◄───────────────────────│                     │                     │
    │ [Response: T=20.5C...] │                     │                     │
    │───────────────────────►│                     │                     │
    │                        │ [HTTP: sensors]     │                     │
    │                        │◄────────────────────│                     │
    │                        │ [JSON: {temp:20.5}] │                     │
    │                        │────────────────────►│                     │
    │                        │                     │ [Telemetry]         │
    │                        │                     │────────────────────►│
    │                        │                     │                     │
```

### Control Flow

```
User                    Website               MycoBrain              MycoBoard
  │                        │                      │                      │
  │ [Click: Red LED]       │                      │                      │
  │───────────────────────►│                      │                      │
  │                        │ [POST: control]      │                      │
  │                        │─────────────────────►│                      │
  │                        │                      │ [Serial: led rgb...] │
  │                        │                      │─────────────────────►│
  │                        │                      │ [OK]                 │
  │                        │                      │◄─────────────────────│
  │                        │ [200 OK]             │                      │
  │                        │◄─────────────────────│                      │
  │ [LED turns red]        │                      │                      │
  │◄───────────────────────│                      │                      │
```

## Docker Deployment

### Always-On Stack

All services run in Docker with automatic restart:

```yaml
# docker-compose.always-on.yml
services:
  mycosoft-website:
    build: ../WEBSITE/website
    ports: ["3000:3000"]
    environment:
      - MYCOBRAIN_SERVICE_URL=http://mycobrain:8003
      - MINDEX_API_URL=http://mindex:8000
    depends_on: [mycobrain, mindex]
    
  mycobrain:
    build: ./services/mycobrain
    ports: ["8003:8003"]
    
  mindex:
    build: ./services/mindex
    ports: ["8000:8000"]
```

### Hardware Override

For USB device access:

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

## Network Configuration

### Internal Docker Network

All services communicate via the `mycosoft-always-on` network:

| Service | Internal URL | External URL |
|---------|--------------|--------------|
| Website | `http://mycosoft-website:3000` | `http://localhost:3000` |
| MycoBrain | `http://mycobrain:8003` | `http://localhost:8003` |
| MINDEX | `http://mindex:8000` | `http://localhost:8000` |

### Environment Variables

```bash
# Website container
MYCOBRAIN_SERVICE_URL=http://mycobrain:8003
MINDEX_API_URL=http://mindex:8000

# MycoBrain container
MYCOBRAIN_HOST=0.0.0.0
MYCOBRAIN_PORT=8003
DEFAULT_SERIAL_PORT=/dev/ttyACM0
```

## NatureOS Integration

The Device Manager is accessible via NatureOS at:

```
http://localhost:3000/natureos/devices
```

### Features

1. **Sensors Tab**: Live environmental data from both BME688 sensors
2. **Controls Tab**: LED color picker, buzzer sounds
3. **Comms Tab**: LoRa, WiFi, Bluetooth status (future)
4. **Analytics Tab**: Historical data charts
5. **Console Tab**: Raw serial terminal
6. **Config Tab**: Device settings
7. **Diagnostics Tab**: System health checks, I2C scan

## MAS Integration

The Multi-Agent System (MAS) uses device data for intelligent automation:

### Agent Access

```python
# Example: Agent querying sensor data
async def get_environment_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:3000/api/mycobrain/mycobrain-ttyACM0/sensors"
        )
        return response.json()
```

### MINDEX Telemetry

Diagnostics and sensor data are logged to MINDEX:

```python
# POST /telemetry/device
{
    "source": "mycobrain-diagnostics",
    "device_id": "mycobrain-ttyACM0",
    "timestamp": "2024-12-30T07:21:58.969Z",
    "data": {
        "board_info": {"board_type": "MycoBoard", ...},
        "tests_passed": 6,
        "tests_total": 6
    }
}
```

## Startup Sequence

### Automated (Docker Compose)

```powershell
# From project root
.\scripts\start-all-persistent.ps1
```

This script:
1. Attaches USB device to WSL2 via `usbipd`
2. Clears any port conflicts
3. Starts all Docker services
4. Waits for health checks

### Manual

```powershell
# 1. Attach USB device
.\scripts\attach-mycoboard-usbipd.ps1

# 2. Start services
docker compose -f docker-compose.always-on.yml \
               -f docker-compose.always-on.hardware.yml \
               up -d

# 3. Connect device
Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/ttyACM0" -Method POST
```

## Troubleshooting

### Service Not Connecting

1. Check Docker containers are running:
   ```bash
   docker ps
   ```

2. Check MycoBrain health:
   ```bash
   curl http://localhost:8003/health
   ```

3. Verify USB passthrough:
   ```powershell
   usbipd list
   wsl ls /dev/ttyACM*
   ```

### Sensor Data Blinking

1. Check sensor caching is enabled in `/api/mycobrain/{port}/sensors`
2. Verify polling interval (should be 2+ seconds)
3. Check for timeout errors in browser console

### Port Locked

1. Clear port locks:
   ```bash
   curl http://localhost:3000/api/mycobrain/ports/clear-locks
   ```

2. Restart MycoBrain container:
   ```bash
   docker restart mycosoft-always-on-mycobrain-1
   ```

## Related Documentation

- [MycoBoard Technical Reference](./MYCOBOARD_TECHNICAL_REFERENCE.md)
- [MycoBrain Service README](../services/mycobrain/README.md)
- [MDP Protocol Specification](./protocols/MDP_V1_SPEC.md)
- [Docker Setup Guide](./INTEGRATIONS_DOCKER_SETUP.md)

---

*Last Updated: December 2024*
*Part of the Mycosoft Multi-Agent System (MAS)*



























