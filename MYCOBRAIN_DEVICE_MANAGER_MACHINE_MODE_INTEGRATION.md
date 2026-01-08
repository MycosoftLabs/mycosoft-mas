# MycoBrain Device Manager - Machine Mode Integration Guide
## Complete Technical Documentation for December 29, 2025 Working Configuration

**Date**: January 6, 2026  
**Purpose**: Share with firmware debugging agent  
**Status**: Pre-ScienceComms upgrade working state

---

## Executive Summary

This document provides a complete technical explanation of how the MycoBrain device manager worked with Machine Mode on the MycoBrain ESP32-S3 board before the ScienceComms upgrade. It includes firmware settings, integration architecture, command protocols, and all working configurations from December 29, 2025.

---

## 1. System Architecture Overview

### 1.1 Complete Integration Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Website (Port 3000)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Device Manager Component                            │   │
│  │  (components/mycobrain-device-manager.tsx)          │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │ HTTP REST API
                      │ POST /api/mycobrain/command
                      │ GET  /api/mycobrain/devices
                      │ GET  /api/mycobrain/telemetry
┌─────────────────────▼───────────────────────────────────────┐
│         MycoBrain Service (Port 8003)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Service                                    │   │
│  │  - Device connection management                      │   │
│  │  - Serial port communication                        │   │
│  │  - Command translation (JSON → CLI)                 │   │
│  │  - Telemetry parsing (NDJSON → JSON)                │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │ Serial Communication
                      │ COM5 (Windows) / /dev/ttyUSB0 (Linux)
                      │ Baud Rate: 115200
                      │ Protocol: Plaintext CLI + NDJSON
┌─────────────────────▼───────────────────────────────────────┐
│         MycoBrain ESP32-S3 (Side-A)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Firmware v3.3.5 (December 29, 2025)                 │   │
│  │  - Machine Mode (NDJSON output)                      │   │
│  │  - Plaintext CLI commands                           │   │
│  │  - NeoPixel control (GPIO15)                         │   │
│  │  - Buzzer control (GPIO16)                           │   │
│  │  - I2C sensor scanning                               │   │
│  │  - BME688 environmental sensors                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

**Command Flow (Website → Board):**
1. User clicks button in Device Manager UI
2. React component calls `/api/mycobrain/command` endpoint
3. Next.js API route forwards to MycoBrain Service (port 8003)
4. Service translates JSON command to CLI format
5. Service sends plaintext command via serial port
6. Firmware receives command and executes
7. Firmware responds with NDJSON (in Machine Mode) or plaintext

**Telemetry Flow (Board → Website):**
1. Firmware sends NDJSON telemetry every 5 seconds (or on command)
2. MycoBrain Service reads serial port continuously
3. Service parses NDJSON lines (one JSON object per line)
4. Service stores telemetry in memory/cache
5. Website polls `/api/mycobrain/telemetry` endpoint
6. Service returns latest telemetry data
7. Device Manager UI updates display

---

## 2. Firmware Configuration (December 29, 2025)

### 2.1 Arduino IDE Settings (Last Known Working)

**Board Configuration:**
- **Board**: ESP32S3 Dev Module
- **USB CDC on boot**: **Enabled** ✅
- **USB DFU on boot**: **Enabled** ✅ (requires USB OTG mode)
- **USB Firmware MSC on boot**: **Disabled**
- **USB Mode**: **Hardware CDC and JTAG**
- **JTAG Adapter**: **Integrated USB JTAG**
- **PSRAM**: **OPI PSRAM** ⚠️ (Note: This may cause issues on some boards)
- **CPU Frequency**: **240 MHz**
- **WiFi Core Debug Level**: **None**
- **Arduino runs on core**: **1**
- **Events run on core**: **1**
- **Flash Mode**: **QIO @ 80 MHz**
- **Flash Size**: **16 MB**
- **Partition Scheme**: **16MB flash, 3MB app / 9.9MB FATFS**
- **Upload Speed**: **921600**
- **Upload Port**: **UART0/Hardware CDC**
- **Erase all flash before upload**: **Disabled**

**Critical Settings:**
```
USB CDC on boot: Enabled
USB Mode: Hardware CDC and JTAG
PSRAM: OPI PSRAM
Flash Mode: QIO @ 80 MHz
Flash Size: 16 MB
Partition Scheme: 16MB flash, 3MB app / 9.9MB FATFS
```

### 2.2 Firmware Version

- **Version**: v3.3.5 (December 29, 2025)
- **Build System**: Arduino IDE
- **Bootloader**: Arduino ESP32-S3 bootloader (20KB)
- **Status**: ✅ **WORKING** (before ScienceComms upgrade)

### 2.3 Hardware Pin Configuration

**Critical Pin Definitions:**
- **NeoPixel (SK6805)**: GPIO15 (NEO_1 net, via 75Ω resistor R11)
- **Buzzer**: GPIO16 (BUZZER net, drives MOSFET Q4)
- **I2C SDA**: GPIO5
- **I2C SCL**: GPIO4
- **Analog Inputs**: GPIO6, GPIO7, GPIO10, GPIO11 (ESP32-S3 specific, NOT GPIO34/35/36/39)
- **MOSFET Outputs**: GPIO12, GPIO13, GPIO14 (OUT_1, OUT_2, OUT_3)

**Important**: The onboard LED is an **SK6805 NeoPixel** (addressable RGB LED), NOT PWM RGB LEDs. It requires NeoPixel protocol (WS2812-class, 800 kHz), not `analogWrite()`.

---

## 3. Machine Mode Protocol

### 3.1 What is Machine Mode?

Machine Mode is a firmware feature that enables **NDJSON (Newline-Delimited JSON)** output format. This allows automated parsing of device responses without human-readable text interference.

### 3.2 Machine Mode Initialization Sequence

When the Device Manager connects to a device, it sends this initialization sequence:

```
1. mode machine    ← Enable machine mode
2. dbg off         ← Disable debug prints
3. fmt json        ← Set output format to JSON
4. scan            ← Trigger I2C scan (returns JSON)
5. status          ← Get device status (returns JSON)
```

**Expected Firmware Behavior:**
- After `mode machine`: All responses become NDJSON (one JSON object per line)
- After `dbg off`: No debug messages printed
- After `fmt json`: All command responses are JSON formatted
- Commands like `scan` and `status` return structured JSON data

### 3.3 NDJSON Format

**Telemetry Example (every 5 seconds):**
```json
{"type":"telemetry","device_id":"mycobrain-001","timestamp":1704067200,"temperature":25.5,"humidity":60.0,"pressure":1013.25,"gas_resistance":50000,"ai1_voltage":3.3,"ai2_voltage":2.5,"i2c_addresses":[118,119]}
{"type":"telemetry","device_id":"mycobrain-001","timestamp":1704067205,"temperature":25.6,"humidity":60.1,"pressure":1013.26,"gas_resistance":50010,"ai1_voltage":3.3,"ai2_voltage":2.5,"i2c_addresses":[118,119]}
```

**Command Response Example:**
```json
{"type":"response","command":"scan","status":"ok","i2c_addresses":[118,119],"devices":[{"address":118,"type":"BME688"},{"address":119,"type":"BME688"}]}
```

**Key Characteristics:**
- One JSON object per line
- Each line is a complete, valid JSON object
- Lines are separated by `\n` (newline)
- No trailing commas
- No array wrapping (each line is independent)

### 3.4 Parsing NDJSON in Device Manager Service

**Python Service Code (pseudocode):**
```python
import serial
import json

def read_ndjson_line(serial_port):
    """Read one NDJSON line from serial port."""
    line = serial_port.readline().decode('utf-8').strip()
    if line:
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None
    return None

def parse_telemetry(serial_port):
    """Continuously parse NDJSON telemetry."""
    while True:
        data = read_ndjson_line(serial_port)
        if data and data.get('type') == 'telemetry':
            # Store telemetry data
            store_telemetry(data)
```

**Service Parsing Rules:**
1. Read serial port line by line
2. Only parse lines that start with `{` (JSON objects)
3. Ignore non-JSON lines (banners, help text, etc.)
4. Extract telemetry data from `type: "telemetry"` objects
5. Extract command responses from `type: "response"` objects

---

## 4. Device Manager Component (Website)

### 4.1 React Component Architecture

**File**: `components/mycobrain-device-manager.tsx`

**Key Features:**
- Device discovery and connection management
- Real-time telemetry display
- Command sending interface
- Port scanning and selection
- Side-A / Side-B selection

### 4.2 Command Sending Flow

**Component Code (simplified):**
```typescript
const sendCommand = async (
  deviceId: string,
  command: string,
  parameters: Record<string, any> = {}
) => {
  try {
    const res = await fetch("/api/mycobrain/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        device_id: deviceId,
        command,
        parameters,
        use_mdp: false,  // Use plaintext CLI, not MDP protocol
      }),
    });

    if (res.ok) {
      const data = await res.json();
      if (data.status === "sent") {
        // Refresh telemetry after command
        setTimeout(() => fetchTelemetry(deviceId), 500);
      }
    }
  } catch (error) {
    alert(`Command error: ${error.message}`);
  }
};
```

**Example Commands:**
```typescript
// NeoPixel control
sendCommand(deviceId, "set_neopixel", {
  led_index: 0,
  r: 255,
  g: 0,
  b: 0,
});

// Buzzer control
sendCommand(deviceId, "set_buzzer", {
  frequency: 1000,
  duration: 200,
});

// I2C scan
sendCommand(deviceId, "i2c_scan", {});
```

### 4.3 Telemetry Polling

**Component Code:**
```typescript
useEffect(() => {
  const interval = setInterval(() => {
    devices.forEach((d) => {
      if (d.status === "connected") {
        fetchTelemetry(d.device_id);
      }
    });
  }, 5000);  // Poll every 5 seconds
  
  return () => clearInterval(interval);
}, [devices]);
```

---

## 5. MycoBrain Service (Backend)

### 5.1 Service Architecture

**Service Endpoints:**
- `GET /health` - Service health check
- `GET /devices` - List connected devices
- `GET /ports` - Scan available serial ports
- `POST /devices/connect/{port}` - Connect to device
- `POST /devices/{device_id}/command` - Send command
- `GET /devices/{device_id}/telemetry` - Get latest telemetry
- `POST /devices/{device_id}/disconnect` - Disconnect device

### 5.2 Command Translation

**Service receives JSON command:**
```json
{
  "device_id": "mycobrain-001",
  "command": "set_neopixel",
  "parameters": {
    "r": 255,
    "g": 0,
    "b": 0
  },
  "use_mdp": false
}
```

**Service translates to CLI format:**
```python
def translate_command(command, parameters):
    if command == "set_neopixel":
        r = parameters.get("r", 0)
        g = parameters.get("g", 0)
        b = parameters.get("b", 0)
        return f"led rgb {r} {g} {b}\n"
    
    elif command == "set_buzzer":
        if parameters.get("off"):
            return "buzzer off\n"
        freq = parameters.get("frequency", 1000)
        dur = parameters.get("duration", 200)
        return f"buzzer {freq} {dur}\n"
    
    elif command == "i2c_scan":
        return "scan\n"
    
    elif command == "status":
        return "status\n"
    
    # ... more command translations
```

**Service sends via serial:**
```python
serial_port.write(cli_command.encode('utf-8'))
```

### 5.3 Telemetry Parsing

**Service reads NDJSON:**
```python
def read_telemetry(serial_port):
    """Read and parse NDJSON telemetry."""
    buffer = ""
    while True:
        char = serial_port.read(1).decode('utf-8', errors='ignore')
        if char == '\n':
            # Complete line received
            if buffer.strip().startswith('{'):
                try:
                    data = json.loads(buffer.strip())
                    if data.get('type') == 'telemetry':
                        return data
                except json.JSONDecodeError:
                    pass
            buffer = ""
        else:
            buffer += char
```

**Service stores telemetry:**
```python
# In-memory storage (simplified)
telemetry_cache = {}

def store_telemetry(device_id, data):
    telemetry_cache[device_id] = {
        "device_id": device_id,
        "timestamp": data.get("timestamp"),
        "telemetry": {
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "pressure": data.get("pressure"),
            "gas_resistance": data.get("gas_resistance"),
            "ai1_voltage": data.get("ai1_voltage"),
            "ai2_voltage": data.get("ai2_voltage"),
            "i2c_addresses": data.get("i2c_addresses", []),
        }
    }
```

---

## 6. Firmware Commands (v3.3.5)

### 6.1 Supported Commands

**LED Control:**
```
led rgb <r> <g> <b>     - Set NeoPixel color (0-255 each)
led off                 - Turn NeoPixel off
led mode off|state|manual  - Set LED mode
```

**Buzzer Control:**
```
buzzer beep            - Play beep (1000Hz, 100ms)
buzzer coin            - Play coin sound (988Hz→1319Hz)
buzzer bump            - Play bump sound
buzzer power           - Play power sound
buzzer 1up             - Play 1up sound
buzzer morgio          - Play morgio jingle (alias: morg)
buzzer off             - Turn buzzer off
```

**I2C Commands:**
```
scan                   - Scan I2C bus and return addresses
```

**Sensor Commands:**
```
status                 - Get device status (JSON in machine mode)
live on                - Enable live sensor output
live off               - Disable live sensor output
```

**Format Control:**
```
fmt lines              - Plaintext output format
fmt json               - JSON output format (for machine mode)
```

**Mode Control:**
```
mode machine           - Enable machine mode (NDJSON output)
mode human             - Disable machine mode (human-readable)
dbg on                 - Enable debug prints
dbg off                - Disable debug prints
```

**BME688 Sensor Commands:**
```
probe                  - Probe BME688 sensors
regs                   - Read BME688 registers
rate <interval>        - Set telemetry rate (seconds)
```

### 6.2 Command Response Format

**In Machine Mode (NDJSON):**
```json
{"type":"response","command":"scan","status":"ok","i2c_addresses":[118,119]}
{"type":"response","command":"status","status":"ok","temperature":25.5,"humidity":60.0,"pressure":1013.25}
```

**In Human Mode (Plaintext):**
```
I2C scan complete. Found 2 devices:
  0x76 (BME688)
  0x77 (BME688)

Device status:
  Temperature: 25.5°C
  Humidity: 60.0%
  Pressure: 1013.25 hPa
```

---

## 7. Integration Flow (Complete Example)

### 7.1 Device Connection Sequence

**Step 1: User clicks "Connect Side-A" in Device Manager**

**Step 2: Website sends connection request:**
```typescript
POST /api/mycobrain/devices
{
  "action": "connect",
  "port": "COM5",
  "side": "side-a",
  "baudrate": 115200
}
```

**Step 3: Service connects to serial port:**
```python
serial_port = serial.Serial(
    port="COM5",
    baudrate=115200,
    timeout=1.0
)
```

**Step 4: Service initializes Machine Mode:**
```python
# Send initialization sequence
serial_port.write(b"mode machine\n")
time.sleep(0.1)
serial_port.write(b"dbg off\n")
time.sleep(0.1)
serial_port.write(b"fmt json\n")
time.sleep(0.1)
serial_port.write(b"scan\n")
```

**Step 5: Service reads NDJSON responses:**
```python
# Read scan response
response = read_ndjson_line(serial_port)
# {"type":"response","command":"scan","status":"ok","i2c_addresses":[118,119]}
```

**Step 6: Service returns device info to website:**
```json
{
  "status": "connected",
  "device_id": "mycobrain-com5-side-a",
  "port": "COM5",
  "side": "side-a",
  "i2c_sensors": [118, 119]
}
```

**Step 7: Website starts polling telemetry:**
```typescript
setInterval(() => {
  fetchTelemetry(deviceId);
}, 5000);
```

### 7.2 Command Execution Example

**User clicks "Red LED" button:**

1. **Website sends command:**
```typescript
POST /api/mycobrain/command
{
  "device_id": "mycobrain-com5-side-a",
  "command": "set_neopixel",
  "parameters": { "r": 255, "g": 0, "b": 0 },
  "use_mdp": false
}
```

2. **Service translates to CLI:**
```python
cli_command = "led rgb 255 0 0\n"
```

3. **Service sends via serial:**
```python
serial_port.write(cli_command.encode('utf-8'))
```

4. **Firmware executes and responds:**
```json
{"type":"response","command":"led","status":"ok","r":255,"g":0,"b":0}
```

5. **Service returns to website:**
```json
{
  "status": "sent",
  "response": {"type":"response","command":"led","status":"ok"}
}
```

6. **Website refreshes telemetry:**
```typescript
setTimeout(() => fetchTelemetry(deviceId), 500);
```

---

## 8. Critical Implementation Details

### 8.1 Serial Port Configuration

**Required Settings:**
- **Baud Rate**: 115200
- **Data Bits**: 8
- **Stop Bits**: 1
- **Parity**: None
- **Flow Control**: None
- **Timeout**: 1.0 seconds (for reading)

**Port Detection:**
- Windows: COM1, COM2, COM3, COM5, etc.
- Linux: /dev/ttyUSB0, /dev/ttyACM0, etc.
- Service scans all available ports and filters for ESP32-S3 devices

### 8.2 NDJSON Parsing Rules

**Service Parsing Strategy:**
1. **Read line by line** from serial port
2. **Filter lines** that start with `{` (JSON objects)
3. **Ignore** non-JSON lines (banners, help text, debug messages)
4. **Parse JSON** using `json.loads()`
5. **Extract telemetry** from `type: "telemetry"` objects
6. **Extract responses** from `type: "response"` objects

**Error Handling:**
- Invalid JSON lines are ignored (not errors)
- Timeout after 1 second if no data received
- Retry logic for command sending (3 attempts)

### 8.3 Command Translation Mapping

**Website Command → Firmware CLI:**

| Website Command | Parameters | Firmware CLI |
|----------------|------------|--------------|
| `set_neopixel` | `{r, g, b}` | `led rgb {r} {g} {b}` |
| `set_neopixel` | `{all_off: true}` | `led off` |
| `set_buzzer` | `{frequency, duration}` | `buzzer {frequency} {duration}` |
| `set_buzzer` | `{off: true}` | `buzzer off` |
| `i2c_scan` | `{}` | `scan` |
| `status` | `{}` | `status` |
| `set_mosfet` | `{mosfet_index, state}` | `mosfet {index} {on/off}` |

### 8.4 Telemetry Schema

**NDJSON Telemetry Object:**
```json
{
  "type": "telemetry",
  "device_id": "mycobrain-001",
  "timestamp": 1704067200,
  "temperature": 25.5,
  "humidity": 60.0,
  "pressure": 1013.25,
  "gas_resistance": 50000,
  "ai1_voltage": 3.3,
  "ai2_voltage": 2.5,
  "ai3_voltage": 1.8,
  "ai4_voltage": 0.0,
  "i2c_addresses": [118, 119],
  "mosfet_states": [false, false, false, false],
  "firmware_version": "3.3.5",
  "uptime_seconds": 3600
}
```

**Service Response Format:**
```json
{
  "status": "ok",
  "device_id": "mycobrain-com5-side-a",
  "side": "side-a",
  "timestamp": "2025-12-29T12:00:00Z",
  "telemetry": {
    "temperature": 25.5,
    "humidity": 60.0,
    "pressure": 1013.25,
    "gas_resistance": 50000,
    "ai1_voltage": 3.3,
    "ai2_voltage": 2.5,
    "i2c_addresses": [118, 119],
    "mosfet_states": [false, false, false, false]
  }
}
```

---

## 9. Known Working Features (December 29, 2025)

### 9.1 ✅ Confirmed Working

- **LED Control**: NeoPixel (GPIO15) responds to `led rgb` commands
- **Buzzer Control**: GPIO16 responds to `buzzer` commands (coin, bump, power, 1up, morgio)
- **I2C Scanning**: `scan` command detects BME688 sensors (0x76, 0x77)
- **Sensor Data**: BME688 sensors provide temperature, humidity, pressure, gas resistance
- **Machine Mode**: NDJSON output works correctly
- **Command Parsing**: Firmware correctly parses CLI commands
- **Telemetry Streaming**: Automatic telemetry every 5 seconds

### 9.2 ⚠️ Limitations

- **No LED Patterns**: Only basic RGB control, no rainbow/chase patterns
- **No Custom Tones**: Only preset sounds, no frequency/duration control
- **No Optical TX**: Not implemented in v3.3.5
- **No Acoustic TX**: Not implemented in v3.3.5
- **No BLE**: Not implemented in v3.3.5
- **No Mesh Networking**: Not implemented in v3.3.5

---

## 10. Troubleshooting Guide

### 10.1 Common Issues

**Issue: Device not responding to commands**
- **Check**: Machine mode initialized? (`mode machine`, `dbg off`, `fmt json`)
- **Check**: Serial port connection active?
- **Check**: Firmware version (must be v3.3.5 or compatible)

**Issue: Telemetry not updating**
- **Check**: Service reading serial port continuously?
- **Check**: NDJSON parsing working? (lines starting with `{`)
- **Check**: Telemetry interval set? (default 5 seconds)

**Issue: Commands not executing**
- **Check**: Command translation correct? (JSON → CLI)
- **Check**: Serial port write successful?
- **Check**: Firmware command parsing working?

**Issue: JSON parsing errors**
- **Check**: Only parsing lines starting with `{`?
- **Check**: Ignoring non-JSON lines (banners, help text)?
- **Check**: NDJSON format correct? (one JSON object per line)

---

## 11. Firmware Requirements for Device Manager

### 11.1 Required Features

1. **Machine Mode Support**
   - `mode machine` command enables NDJSON output
   - `dbg off` disables debug prints
   - `fmt json` sets JSON output format

2. **NDJSON Telemetry**
   - Automatic telemetry every N seconds (configurable)
   - Each telemetry packet is one JSON object on one line
   - Format: `{"type":"telemetry",...}\n`

3. **Command Responses**
   - All commands return JSON responses in machine mode
   - Format: `{"type":"response","command":"...","status":"ok",...}\n`

4. **CLI Command Support**
   - `led rgb <r> <g> <b>` - NeoPixel control
   - `buzzer <command>` - Buzzer control
   - `scan` - I2C bus scan
   - `status` - Device status

### 11.2 Recommended Features

- **Telemetry Interval Control**: `rate <seconds>` command
- **Live Output Toggle**: `live on/off` command
- **MOSFET Control**: `mosfet <index> <on/off>` command
- **Sensor Commands**: `probe`, `regs` for BME688

---

## 12. Summary

### 12.1 Key Points

1. **Machine Mode** enables NDJSON output for automated parsing
2. **Initialization sequence**: `mode machine`, `dbg off`, `fmt json`
3. **Command translation**: Website JSON → Service CLI → Firmware
4. **Telemetry parsing**: Service reads NDJSON lines, extracts telemetry
5. **Firmware v3.3.5** (December 29, 2025) was the last known working version

### 12.2 Critical Settings

- **USB CDC on boot**: Enabled
- **USB Mode**: Hardware CDC and JTAG
- **PSRAM**: OPI PSRAM
- **Flash Mode**: QIO @ 80 MHz
- **Flash Size**: 16 MB
- **Partition Scheme**: 16MB flash, 3MB app / 9.9MB FATFS
- **Baud Rate**: 115200
- **NeoPixel Pin**: GPIO15 (SK6805, not PWM)
- **Buzzer Pin**: GPIO16

### 12.3 Integration Checklist

- [x] Device Manager UI component created
- [x] MycoBrain Service API endpoints implemented
- [x] Command translation (JSON → CLI) working
- [x] NDJSON telemetry parsing working
- [x] Machine mode initialization sequence implemented
- [x] Firmware v3.3.5 supports all required commands
- [x] Serial port communication stable
- [x] Real-time telemetry updates working

---

## 13. Files and Locations

### 13.1 Website Components
- `components/mycobrain-device-manager.tsx` - Device Manager UI
- `app/api/mycobrain/command/route.ts` - Command API endpoint
- `app/api/mycobrain/devices/route.ts` - Device management endpoint
- `app/api/mycobrain/telemetry/route.ts` - Telemetry endpoint

### 13.2 Service Code
- `services/mycobrain/mycobrain_service.py` - FastAPI service (port 8003)
- Service handles serial communication, command translation, telemetry parsing

### 13.3 Firmware
- `firmware/MycoBrain_SideA/` - Arduino IDE firmware (v3.3.5)
- Last known working: December 29, 2025

---

**Document Version**: 1.0  
**Last Updated**: January 6, 2026  
**Status**: Complete technical documentation for firmware debugging agent
