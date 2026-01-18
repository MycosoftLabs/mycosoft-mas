# MycoBrain System Architecture
**Complete Holistic Overview**  
**Date**: January 16, 2026

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Hardware Architecture](#hardware-architecture)
3. [Firmware Architecture](#firmware-architecture)
4. [Service Architecture](#service-architecture)
5. [Website Integration](#website-integration)
6. [Data Flow](#data-flow)
7. [Protocol Specifications](#protocol-specifications)
8. [Network Topology](#network-topology)
9. [Integration Points](#integration-points)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

MycoBrain is an environmental monitoring and control system designed for mycology research and mushroom cultivation. It consists of ESP32-S3 hardware devices, a FastAPI service layer, a Next.js web interface, and integration with the Mycosoft Multi-Agent System (MAS).

### Key Components
1. **Hardware**: Dual ESP32-S3 boards with sensors and actuators
2. **Firmware**: Arduino-based firmware with CLI and JSON protocols
3. **Service**: FastAPI service for device management (port 8003)
4. **Website**: Next.js Device Manager UI (port 3000)
5. **MAS Integration**: Agent-based system integration
6. **N8n Workflows**: Automation and data forwarding

---

## Hardware Architecture

### Dual ESP32-S3 Design

```
┌─────────────────────────────────────────────────────────┐
│                    MycoBrain Board                       │
│                                                          │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │     Side-A (Sensor)   │    │   Side-B (Router)    │  │
│  │     ESP32-S3          │◄──►│     ESP32-S3         │  │
│  │                       │UART│                      │  │
│  │  - BME688 sensors     │    │  - LoRa SX1262       │  │
│  │  - NeoPixel (GPIO15)  │    │  - UART routing      │  │
│  │  - Buzzer (GPIO16)    │    │  - Command channel   │  │
│  │  - MOSFETs (12/13/14) │    │                      │  │
│  │  - I2C bus (GPIO4/5)  │    │                      │  │
│  │  - Analog (6/7/10/11) │    │                      │  │
│  └──────────────────────┘    └──────────────────────┘  │
│           │                            │                │
│           │ USB-C                      │ USB-C          │
│           │ (Data + Power)             │ (Power)        │
└───────────┼────────────────────────────┼────────────────┘
            │                            │
            ▼                            ▼
       Computer                     Power Source
```

### Side-A (Sensor MCU)
**Primary Functions:**
- Environmental sensing (BME688 × 2)
- NeoPixel LED control
- Buzzer control
- MOSFET switching
- I2C peripheral management
- Analog input reading

**Connections:**
- USB-C: Data + Power (connects to computer)
- I2C: BME688 sensors at 0x76 and 0x77
- GPIO15: SK6805 NeoPixel
- GPIO16: Piezo buzzer via MOSFET
- GPIO12/13/14: MOSFET outputs

### Side-B (Router MCU)
**Primary Functions:**
- UART ↔ LoRa routing
- Command acknowledgements
- LoRa communication (SX1262)

**Connections:**
- USB-C: Power only
- UART: Connected to Side-A
- SPI: LoRa module (SX1262)

---

## Firmware Architecture

### Firmware Layers

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Sensors   │  │  Actuators  │  │   Commands  │    │
│  │  (BME688)   │  │(LED/Buzzer) │  │   (CLI/JSON)│    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Protocol Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  CLI Parser │  │ JSON Parser │  │ Machine Mode│    │
│  │             │  │             │  │   (NDJSON)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Communication Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    Serial   │  │    UART     │  │    LoRa     │    │
│  │  (USB CDC)  │  │  (Side-B)   │  │  (SX1262)   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Hardware Layer                        │
│  ESP32-S3 + Peripherals (NeoPixel, Buzzer, Sensors)    │
└─────────────────────────────────────────────────────────┘
```

### Firmware Modules

**1. Command Handler**
- Parses CLI commands (`led rgb 255 0 0`)
- Parses JSON commands (`{"cmd":"led","r":255}`)
- Routes to appropriate handlers

**2. Sensor Manager**
- BME688 BSEC2 integration
- I2C scanning
- Analog input reading
- Telemetry generation

**3. Actuator Controller**
- NeoPixel control (NeoPixelBus/FastLED)
- Buzzer tone generation
- MOSFET switching

**4. Communication Manager**
- Serial I/O (USB CDC)
- UART routing (to Side-B)
- Machine Mode formatting

---

## Service Architecture

### MycoBrain Service (Port 8003)

```
┌─────────────────────────────────────────────────────────┐
│              MycoBrain FastAPI Service                   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              API Layer (FastAPI)                  │  │
│  │  /health, /devices, /ports, /command, /telemetry │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Device Connection Manager                │  │
│  │  - Port scanning                                  │  │
│  │  - Device registration                            │  │
│  │  - Connection lifecycle                           │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Serial Communication Layer              │  │
│  │  - PySerial interface                             │  │
│  │  - Command translation (JSON → CLI)               │  │
│  │  - Response parsing (CLI/NDJSON → JSON)           │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │            Protocol Layer (MDP v1)                │  │
│  │  - COBS framing                                   │  │
│  │  - CRC16 checksums                                │  │
│  │  - Message types (TELEMETRY, COMMAND, EVENT, ACK)│  │
│  └──────────────────┬───────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Machine Mode Handler                 │  │
│  │  - NDJSON parsing                                 │  │
│  │  - Telemetry aggregation                          │  │
│  │  - State management                               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Service Components

**1. Device Manager** (`services/mycobrain/`)
- Device connection management
- Serial port communication
- Command queue management
- Telemetry buffering

**2. Machine Mode Handler** (`services/mycobrain/machine_mode.py`)
- NDJSON parsing
- Telemetry aggregation
- State tracking

**3. Protocol Handler** (`services/mycobrain/protocol.py`)
- MDP v1 encoding/decoding
- COBS framing
- CRC16 validation

**4. MAS Integration** (`services/mycobrain/mas_integration.py`)
- Agent communication
- Event forwarding
- Data synchronization

---

## Website Integration

### Device Manager UI

```
┌─────────────────────────────────────────────────────────┐
│          Device Manager (React Component)                │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Device Status Panel                  │  │
│  │  - Connection state                               │  │
│  │  - MAC address                                    │  │
│  │  - Firmware version                               │  │
│  │  - Last seen timestamp                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Control Panel                        │  │
│  │  ┌────────────────┐  ┌────────────────┐          │  │
│  │  │  NeoPixel      │  │  Buzzer        │          │  │
│  │  │  - Color picker│  │  - Presets     │          │  │
│  │  │  - Brightness  │  │  - Custom tone │          │  │
│  │  └────────────────┘  └────────────────┘          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │            Telemetry Display                      │  │
│  │  - Temperature (°C)                               │  │
│  │  - Humidity (%)                                   │  │
│  │  - Pressure (hPa)                                 │  │
│  │  - Gas Resistance (Ω)                             │  │
│  │  - IAQ (Indoor Air Quality)                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │           I2C Peripheral Scanner                  │  │
│  │  - Scan button                                    │  │
│  │  - Detected devices list                          │  │
│  │  - Device addresses (0x76, 0x77, etc.)            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### API Routes

**Location**: `app/api/mycobrain/`

**Routes:**
```
/api/mycobrain/command           - POST - Send command
/api/mycobrain/devices           - GET  - List devices
/api/mycobrain/telemetry         - GET  - Get telemetry
/api/mycobrain/[port]/sensors    - GET  - Sensor data
/api/mycobrain/[port]/peripherals - GET  - I2C scan
/api/mycobrain/[port]/control    - POST - Control command
```

---

## Data Flow

### Command Flow (Website → Board)

```
User clicks "Coin" button
  ↓
React onClick handler
  ↓
fetch('/api/mycobrain/command', {
  method: 'POST',
  body: JSON.stringify({
    device_id: 'mycobrain-side-a-COM5',
    command: { command_type: 'buzzer', pattern: 'coin' }
  })
})
  ↓
Next.js API Route (/api/mycobrain/command/route.ts)
  ↓
Forward to Service: POST http://localhost:8003/devices/{device_id}/command
  ↓
MycoBrain Service (FastAPI)
  ↓
Command Translation: {command_type: 'buzzer', pattern: 'coin'} → "coin\r\n"
  ↓
Serial Write (115200 baud)
  ↓
MycoBrain ESP32-S3 (Side-A)
  ↓
Firmware Command Parser
  ↓
Buzzer Handler (tone(BUZZER_PIN, freq, duration))
  ↓
GPIO16 → MOSFET → Piezo Buzzer
  ↓
🔊 Sound plays!
```

### Telemetry Flow (Board → Website)

```
BME688 Sensor (0x76, 0x77)
  ↓
I2C Read (GPIO4/5)
  ↓
BSEC2 Processing (IAQ calculation)
  ↓
Firmware Telemetry Generator
  ↓
Machine Mode Formatter (NDJSON)
  ↓
Serial Write: {"type":"telemetry","sensor":"AMB","tC":25.5,...}\n
  ↓
MycoBrain Service (Serial Read)
  ↓
NDJSON Parser
  ↓
Telemetry Buffer (in-memory cache)
  ↓
API Endpoint: GET /devices/{device_id}/telemetry
  ↓
Next.js API Route
  ↓
React Component State Update
  ↓
UI Display (temperature, humidity, etc.)
```

---

## Protocol Specifications

### CLI Protocol (Plaintext)

**Format**: `command [arg1] [arg2] ...\r\n`

**Examples:**
```
led rgb 255 0 0\r\n
coin\r\n
status\r\n
scan\r\n
```

**Responses:**
```
LED manual rgb=255,0,0
[coin sound plays]
AMB addr=0x77 T=25.5C RH=60.2% P=1013.25hPa ...
I2C scan: found: 0x76, found: 0x77
```

### JSON Protocol (Machine Mode)

**Format**: `{"cmd":"command","param1":value1,...}\r\n`

**Examples:**
```json
{"cmd":"led","r":255,"g":0,"b":0}
{"cmd":"buzzer","pattern":"coin"}
{"cmd":"status"}
{"cmd":"scan"}
```

**Responses (NDJSON)**:
```json
{"type":"ack","cmd":"led","status":"ok"}
{"type":"ack","cmd":"buzzer","status":"ok"}
{"type":"telemetry","sensor":"AMB","tC":25.5,"rh":60.2}
{"type":"periph","addr":"0x76","name":"BME688"}
```

### MDP v1 Protocol (Binary)

**Frame Structure:**
```
[0x00] [COBS-encoded payload] [0x00] [CRC16-LE]
```

**Message Types:**
- `0x01` - TELEMETRY
- `0x02` - COMMAND
- `0x03` - EVENT
- `0x04` - ACK

**Payload (JSON)**:
```json
{
  "type": "telemetry",
  "device_id": "mycobrain-001",
  "timestamp": 1234567890,
  "data": {
    "temperature": 25.5,
    "humidity": 60.2
  }
}
```

---

## Network Topology

### Local Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Local Network                         │
│                                                          │
│  ┌──────────────┐                                       │
│  │   Computer   │                                       │
│  │              │                                       │
│  │  ┌────────┐  │  USB-C                               │
│  │  │Website │◄─┼──────────┐                           │
│  │  │:3000   │  │          │                           │
│  │  └────┬───┘  │          │                           │
│  │       │      │          │                           │
│  │       │HTTP  │          │                           │
│  │       ▼      │          │                           │
│  │  ┌────────┐  │          │                           │
│  │  │Service │  │          │                           │
│  │  │:8003   │  │          │                           │
│  │  └────┬───┘  │          │                           │
│  │       │      │          │                           │
│  │       │Serial│          │                           │
│  │       ▼      │          ▼                           │
│  │  ┌────────┐  │  ┌──────────────┐                   │
│  │  │ COM5   │◄─┼──┤ MycoBrain #1 │                   │
│  │  │ COM7   │◄─┼──┤ MycoBrain #2 │                   │
│  │  └────────┘  │  └──────────────┘                   │
│  └──────────────┘                                       │
│                                                          │
│  ┌──────────────┐                                       │
│  │   N8n        │                                       │
│  │   :5678      │                                       │
│  │              │                                       │
│  │  Workflows:  │                                       │
│  │  - Telemetry │                                       │
│  │  - Modem     │                                       │
│  └──────┬───────┘                                       │
│         │                                                │
│         │HTTP                                            │
│         ▼                                                │
│  ┌──────────────┐                                       │
│  │   MINDEX     │                                       │
│  │   :8000      │                                       │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

### LoRa Network (Future)

```
┌─────────────────────────────────────────────────────────┐
│                    LoRa Network                          │
│                                                          │
│  ┌──────────────┐                                       │
│  │   Gateway    │                                       │
│  │  (Side-B)    │                                       │
│  │              │                                       │
│  │  LoRa RX/TX  │                                       │
│  └──────┬───────┘                                       │
│         │                                                │
│         │LoRa (SX1262, 915MHz)                          │
│         │                                                │
│    ┌────┴────┬────────┬────────┐                       │
│    ▼         ▼        ▼        ▼                       │
│  ┌────┐   ┌────┐   ┌────┐   ┌────┐                    │
│  │MB-1│   │MB-2│   │MB-3│   │MB-4│                    │
│  │    │   │    │   │    │   │    │                    │
│  │Side│   │Side│   │Side│   │Side│                    │
│  │ -A │   │ -A │   │ -A │   │ -A │                    │
│  └────┘   └────┘   └────┘   └────┘                    │
│  Remote   Remote   Remote   Remote                     │
│  Sensors  Sensors  Sensors  Sensors                    │
└─────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. MINDEX Integration

**Purpose**: Store and query MycoBrain telemetry data

**Endpoints Used:**
- `POST /telemetry/mycobrain/ingest` - Ingest telemetry
- `GET /telemetry/mycobrain` - Query telemetry
- `POST /devices/mycobrain/register` - Register device
- `GET /devices?device_type=mycobrain` - List devices

**Data Flow:**
```
MycoBrain → Service → N8n Workflow → MINDEX API → PostgreSQL
```

### 2. NatureOS Integration

**Purpose**: Environmental monitoring and control

**Features:**
- Device widget in NatureOS dashboard
- Real-time telemetry display
- Control interface
- Alert system

**Location**: `components/natureos/mycobrain-widget.tsx`

### 3. MAS Agent Integration

**Purpose**: Multi-agent system coordination

**Agents:**
- **Device Agent**: Manages device connections
- **Ingestion Agent**: Ingests telemetry to MINDEX
- **Telemetry Forwarder**: Forwards data to multiple destinations

**Location**: `mycosoft_mas/agents/mycobrain/`

### 4. N8n Workflow Integration

**Purpose**: Automation and data processing

**Workflows:**
- **Workflow 13**: Telemetry forwarder
- **Workflow 14**: Optical/acoustic modem handler

**Location**: `n8n/workflows/`

---

## Deployment Architecture

### Development Environment (Current)

```
Windows PC (localhost)
  ├── Website (Next.js) - Port 3000
  ├── MycoBrain Service (FastAPI) - Port 8003
  ├── N8n - Port 5678
  ├── MINDEX - Port 8000
  └── MycoBrain Devices - COM5, COM7 (USB Serial)
```

### Production Environment (Planned)

```
Ubuntu Server
  ├── Docker Compose Stack
  │   ├── Website Container - Port 3000
  │   ├── MycoBrain Service Container - Port 8003
  │   │   └── USB Passthrough (/dev/ttyUSB0, /dev/ttyUSB1)
  │   ├── N8n Container - Port 5678
  │   ├── MINDEX Container - Port 8000
  │   ├── PostgreSQL Container - Port 5432
  │   ├── Redis Container - Port 6379
  │   └── Qdrant Container - Port 6333
  │
  └── MycoBrain Devices - /dev/ttyUSB0, /dev/ttyUSB1
```

---

## Security Architecture

### Authentication
- **API Keys**: Per-device API keys for MINDEX ingestion
- **Service Auth**: Internal service-to-service authentication
- **CORS**: Configured for localhost:3000 → localhost:8003

### Data Security
- **Serial Communication**: Unencrypted (local USB)
- **HTTP APIs**: Local network only (no TLS required)
- **LoRa Communication**: Encrypted (future)

---

## Monitoring and Observability

### Metrics
- Device connection status
- Telemetry update frequency
- Command success rate
- Serial communication errors
- Sensor health status

### Logging
- Service logs: `services/mycobrain/logs/`
- Firmware logs: Serial output
- N8n logs: Workflow execution logs

### Alerts
- Device disconnection
- Sensor failure
- Temperature/humidity thresholds
- IAQ warnings

---

## Performance Characteristics

### Latency
- **Command latency**: < 100ms (website → board)
- **Telemetry update**: Every 5 seconds
- **I2C scan**: ~1 second
- **Serial communication**: 115200 baud (~11.5 KB/s)

### Throughput
- **Telemetry rate**: ~200 bytes every 5 seconds per device
- **Command rate**: Limited by serial baud rate
- **Max devices**: Limited by available COM ports (~10-20)

### Resource Usage
- **RAM (ESP32-S3)**: ~20KB (6% of 327KB)
- **Flash (ESP32-S3)**: ~320KB (5% of 6.5MB)
- **Service RAM**: ~50MB
- **Service CPU**: < 5%

---

## Future Enhancements

### Firmware
1. **LoRa Communication**: Enable Side-B router functionality
2. **OTA Updates**: Over-the-air firmware updates
3. **Power Management**: Sleep modes for battery operation
4. **Additional Sensors**: Support for more I2C devices

### Service
1. **WebSocket Support**: Real-time telemetry streaming
2. **Multi-Device Management**: Improved scaling
3. **Data Persistence**: Local database for telemetry
4. **Alert System**: Threshold-based alerts

### Website
1. **Real-Time Charts**: Telemetry visualization
2. **Historical Data**: Time-series analysis
3. **Device Configuration**: Remote firmware configuration
4. **Batch Operations**: Control multiple devices

---

## Appendix

### Glossary
- **BME688**: Bosch environmental sensor (temperature, humidity, pressure, gas)
- **BSEC2**: Bosch Sensortec Environmental Cluster 2 (IAQ algorithm)
- **COBS**: Consistent Overhead Byte Stuffing (framing protocol)
- **IAQ**: Indoor Air Quality index
- **MDP**: Mycosoft Device Protocol
- **NDJSON**: Newline-Delimited JSON
- **NeoPixel**: Addressable RGB LED (WS2812-compatible)
- **PSRAM**: Pseudo-Static RAM (external RAM)

### References
- ESP32-S3 Datasheet: https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf
- BME688 Datasheet: https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme688/
- BSEC2 Library: https://github.com/boschsensortec/Bosch-BSEC2-Library
- NeoPixelBus Library: https://github.com/Makuna/NeoPixelBus

---

**Document Version**: 1.0  
**Last Updated**: January 16, 2026  
**Status**: Complete system architecture documented
