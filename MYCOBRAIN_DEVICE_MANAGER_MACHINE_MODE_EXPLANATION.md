# MycoBrain Device Manager with Machine Mode - Complete Technical Explanation

## Overview

This document explains how the Device Manager integrated with the MycoBrain board using **Machine Mode** (NDJSON protocol). This is for sharing with another agent debugging the firmware.

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Website (Port 3000)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Device Manager Component                            │   │
│  │  (components/mycobrain-device-manager.tsx)          │   │
│  │  - React UI for device control                       │   │
│  │  - Polls telemetry every 2-5 seconds                 │   │
│  │  - Sends commands via API routes                     │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                         │ HTTP POST/GET
                         │ /api/mycobrain/*
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Next.js API Routes                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /api/mycobrain/devices  (GET/POST)                  │   │
│  │  /api/mycobrain/ports    (GET)                        │   │
│  │  /api/mycobrain/command  (POST)                       │   │
│  │  /api/mycobrain/telemetry (GET)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                         │ HTTP Forward
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         MycoBrain Service (Port 8003)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Service                                      │   │
│  │  - Manages serial port connections                    │   │
│  │  - Handles device state tracking                      │   │
│  │  - Parses NDJSON responses                            │   │
│  │  - Converts commands to serial format                 │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                         │ Serial (115200 baud)
                         │ pyserial library
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              MycoBrain Board (ESP32-S3)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Side-A (Sensor MCU) - COM5                            │   │
│  │  - Handles sensors, I2C, analog inputs                │   │
│  │  - Controls NeoPixel (GPIO15)                         │   │
│  │  - Controls Buzzer (GPIO16)                            │   │
│  │  - Controls MOSFET outputs (GPIO12/13/14)            │   │
│  │                                                        │   │
│  │  Side-B (Router MCU) - COM6                           │   │
│  │  - Handles LoRa routing                               │   │
│  │  - UART communication bridge                          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Machine Mode Protocol (NDJSON)

### What is Machine Mode?

**Machine Mode** is a firmware feature that outputs structured data in **NDJSON (Newline-Delimited JSON)** format instead of human-readable plaintext. This makes it easier for automated systems to parse responses.

### Enabling Machine Mode

**Command to enable:**
```
mode machine
```

**Command to disable:**
```
mode human
```

### NDJSON Format

In machine mode, the firmware outputs JSON objects, one per line, terminated by newline (`\n`):

```
{"type":"status","device_id":"mycobrain-001","firmware":"3.3.5","uptime":1234}
{"type":"telemetry","temperature":25.5,"humidity":60.0,"pressure":1013.25}
{"type":"response","command":"set_neopixel","status":"ok"}
{"type":"error","message":"Invalid command"}
```

**Key characteristics:**
- Each line is a complete, valid JSON object
- Lines are separated by `\n` (newline character)
- No trailing commas
- No array wrapping (each object is independent)
- Can be parsed line-by-line without buffering entire response

---

## Device Manager Component Flow

### 1. Initial Connection

**User Action:** Click "Connect Side-A" or "Connect Side-B" button

**Component Code:**
```typescript
const connectDevice = async (port: string, side: "side-a" | "side-b" = "side-a") => {
  const res = await fetch("/api/mycobrain/devices", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action: "connect",
      port,           // e.g., "COM5"
      side,           // "side-a" or "side-b"
      baudrate: 115200,
    }),
  });
}
```

**Service Processing:**
1. Opens serial port using `pyserial` library
2. Configures: 115200 baud, 8N1, timeout=1.0s
3. Sends initialization sequence:
   - `mode machine` - Enable NDJSON output
   - `fmt json` - Ensure JSON format
   - `status` - Get initial device status
4. Parses NDJSON response to extract device info
5. Returns device_id and connection status

**Expected Firmware Response:**
```
{"type":"response","command":"mode","status":"ok","mode":"machine"}
{"type":"response","command":"fmt","status":"ok","format":"json"}
{"type":"status","device_id":"mycobrain-001","firmware":"3.3.5","side":"A","uptime":1234}
```

---

### 2. Sending Commands

**User Action:** Click button (e.g., "Red" LED, "Beep" Buzzer, "Scan I2C")

**Component Code:**
```typescript
const sendCommand = async (
  deviceId: string,
  command: string,
  parameters: Record<string, any> = {}
) => {
  const res = await fetch("/api/mycobrain/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      device_id: deviceId,
      command,        // e.g., "set_neopixel", "set_buzzer", "i2c_scan"
      parameters,     // e.g., {r:255, g:0, b:0}
      use_mdp: false, // Use plain JSON, not MDP v1 protocol
    }),
  });
}
```

**Command Translation:**

The service converts high-level commands to firmware-specific formats:

| Device Manager Command | Firmware Command Format |
|------------------------|------------------------|
| `set_neopixel` with `{r:255, g:0, b:0}` | `led red` or JSON: `{"command":"set_neopixel","r":255,"g":0,"b":0}` |
| `set_buzzer` with `{frequency:1000, duration:200}` | `buzzer beep` or JSON: `{"command":"set_buzzer","frequency":1000,"duration":200}` |
| `i2c_scan` | `scan` or JSON: `{"command":"i2c_scan"}` |
| `set_mosfet` with `{mosfet_index:0, state:true}` | JSON: `{"command":"set_mosfet","index":0,"state":true}` |

**Service Serial Communication:**

```python
# Pseudo-code for service command sending
def send_command(port: str, command: str, params: dict):
    ser = serial.Serial(port, 115200, timeout=1.0)
    
    # Build command JSON
    cmd_json = {
        "command": command,
        **params
    }
    
    # Send as JSON string + newline
    cmd_str = json.dumps(cmd_json) + "\n"
    ser.write(cmd_str.encode('utf-8'))
    
    # Read response (NDJSON)
    response_lines = []
    start_time = time.time()
    while time.time() - start_time < 2.0:  # 2 second timeout
        line = ser.readline().decode('utf-8').strip()
        if line:
            try:
                response_lines.append(json.loads(line))
                # Check if we got a response/status/error type
                if any(r.get('type') in ['response', 'status', 'error'] for r in response_lines):
                    break
            except json.JSONDecodeError:
                continue
    
    return response_lines
```

**Expected Firmware Response (NDJSON):**

For `set_neopixel`:
```
{"type":"response","command":"set_neopixel","status":"ok","r":255,"g":0,"b":0}
```

For `i2c_scan`:
```
{"type":"response","command":"i2c_scan","status":"ok","devices":[0x76,0x77]}
```

For errors:
```
{"type":"error","message":"Invalid command","command":"unknown"}
```

---

### 3. Telemetry Polling

**Component Code:**
```typescript
// Polls every 2-5 seconds for connected devices
useEffect(() => {
  const interval = setInterval(() => {
    devices.forEach((d) => {
      if (d.status === "connected") {
        fetchTelemetry(d.device_id);
      }
    });
  }, 5000);  // 5 second interval
  
  return () => clearInterval(interval);
}, [devices]);

const fetchTelemetry = async (deviceId: string) => {
  const res = await fetch(`/api/mycobrain/telemetry?device_id=${deviceId}`);
  const data = await res.json();
  if (data.status === "ok" && data.telemetry) {
    setTelemetry((prev) => ({
      ...prev,
      [deviceId]: data,
    }));
  }
}
```

**Service Telemetry Handling:**

The service continuously reads from the serial port and buffers NDJSON telemetry messages:

```python
# Pseudo-code for telemetry reading
def read_telemetry(port: str):
    ser = serial.Serial(port, 115200, timeout=1.0)
    buffer = ""
    
    while True:
        data = ser.read(ser.in_waiting or 1)
        if data:
            buffer += data.decode('utf-8', errors='ignore')
            
            # Process complete lines
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line:
                    try:
                        msg = json.loads(line)
                        if msg.get('type') == 'telemetry':
                            # Store telemetry
                            store_telemetry(device_id, msg)
                    except json.JSONDecodeError:
                        continue
```

**Expected Firmware Telemetry (NDJSON):**

The firmware should send periodic telemetry (every 5-10 seconds) in machine mode:

```
{"type":"telemetry","timestamp":1234567890,"temperature":25.5,"humidity":60.0,"pressure":1013.25,"gas_resistance":50000,"ai1_voltage":3.3,"ai2_voltage":2.5,"mosfet_states":[false,false,false,false],"i2c_addresses":[0x76,0x77]}
```

---

## Command Reference

### Supported Commands in Device Manager

#### 1. NeoPixel Control

**Device Manager:** `sendCommand(deviceId, "set_neopixel", {r:255, g:0, b:0})`

**Firmware Command Options:**
- Plaintext: `led red`, `led green`, `led blue`, `led off`
- JSON: `{"command":"set_neopixel","r":255,"g":0,"b":0}`

**Expected Response:**
```
{"type":"response","command":"set_neopixel","status":"ok","r":255,"g":0,"b":0}
```

**Hardware Details:**
- **Pin:** GPIO15 (NeoPixel data line, SK6805 LED)
- **Protocol:** WS2812-class (800 kHz, one-wire)
- **Note:** NOT PWM RGB on GPIO12/13/14 (those are MOSFET outputs)

---

#### 2. Buzzer Control

**Device Manager:** `sendCommand(deviceId, "set_buzzer", {frequency:1000, duration:200})`

**Firmware Command Options:**
- Plaintext: `buzzer beep`, `buzzer coin`, `buzzer off`
- JSON: `{"command":"set_buzzer","frequency":1000,"duration":200}`

**Expected Response:**
```
{"type":"response","command":"set_buzzer","status":"ok","frequency":1000,"duration":200}
```

**Hardware Details:**
- **Pin:** GPIO16 (PWM buzzer control)
- **Frequency Range:** 100-5000 Hz typical
- **Duration:** Milliseconds

---

#### 3. I2C Scan

**Device Manager:** `sendCommand(deviceId, "i2c_scan", {})`

**Firmware Command Options:**
- Plaintext: `scan`
- JSON: `{"command":"i2c_scan"}`

**Expected Response:**
```
{"type":"response","command":"i2c_scan","status":"ok","devices":[118,119]}
```
(Addresses in decimal, typically 0x76=118, 0x77=119 for BME688 sensors)

---

#### 4. MOSFET Control

**Device Manager:** `sendCommand(deviceId, "set_mosfet", {mosfet_index:0, state:true})`

**Firmware Command:**
- JSON: `{"command":"set_mosfet","index":0,"state":true}`

**Expected Response:**
```
{"type":"response","command":"set_mosfet","status":"ok","index":0,"state":true}
```

**Hardware Details:**
- **Pins:** GPIO12 (MOSFET 0), GPIO13 (MOSFET 1), GPIO14 (MOSFET 2)
- **Note:** These are NOT connected to the NeoPixel LED

---

#### 5. Status Query

**Device Manager:** Automatically sent on connection

**Firmware Command:**
- Plaintext: `status`
- JSON: `{"command":"status"}`

**Expected Response:**
```
{"type":"status","device_id":"mycobrain-001","firmware":"3.3.5","side":"A","uptime":1234,"mac_address":"AA:BB:CC:DD:EE:FF"}
```

---

## Serial Port Configuration

### Connection Parameters

- **Baud Rate:** 115200
- **Data Bits:** 8
- **Stop Bits:** 1
- **Parity:** None
- **Flow Control:** None
- **Timeout:** 1.0 seconds (for read operations)

### Port Identification

**Windows:**
- Side-A: Typically `COM5` or `COM7`
- Side-B: Typically `COM6` or `COM8`

**Linux/Mac:**
- Side-A: `/dev/ttyUSB0` or `/dev/ttyACM0`
- Side-B: `/dev/ttyUSB1` or `/dev/ttyACM1`

**Detection:**
The service scans available serial ports and identifies ESP32-S3 devices by VID/PID:
- **VID:** `0x303A` (Espressif)
- **PID:** `0x1001` (ESP32-S3)

---

## Error Handling

### Common Issues

#### 1. Port Not Found
**Error:** `SerialException: could not open port 'COM5': PermissionError`

**Causes:**
- Port already in use by another application
- Device not connected
- Wrong port name

**Solution:**
- Check Device Manager (Windows) or `ls /dev/tty*` (Linux)
- Ensure no other serial monitor is open
- Try different USB port/cable

---

#### 2. No Response from Firmware

**Symptoms:**
- Commands sent but no NDJSON response
- Timeout errors

**Causes:**
- Machine mode not enabled
- Firmware crashed/reset loop
- Wrong baud rate
- Serial buffer overflow

**Solution:**
- Send `mode machine` command first
- Check serial monitor for boot messages
- Verify firmware is running (look for "MycoBrain" or "ready" messages)
- Increase serial buffer size if needed

---

#### 3. Invalid JSON Parsing

**Error:** `json.JSONDecodeError: Expecting value`

**Causes:**
- Firmware outputting plaintext instead of JSON
- Incomplete JSON line (buffer issue)
- Corrupted serial data

**Solution:**
- Ensure `mode machine` is enabled
- Check that `fmt json` is set
- Verify serial connection stability
- Add error recovery/retry logic

---

#### 4. Brownout/Reset Loops

**Symptoms:**
- Continuous resets visible in serial monitor
- `E BOD: Brownout detector was triggered` messages

**Causes:**
- Insufficient USB power (PC USB ports are weak)
- Power supply instability

**Solution:**
- Use wall charger/USB-C power adapter (5V, 2A+ recommended)
- Connect Side-A and Side-B to separate power sources if needed
- Check for short circuits or excessive current draw

---

## Integration Points

### 1. Website → API Route

**File:** `app/api/mycobrain/command/route.ts` (or similar)

**Function:**
- Receives HTTP POST with command JSON
- Forwards to MycoBrain service on port 8003
- Returns response to Device Manager component

---

### 2. API Route → MycoBrain Service

**Service Endpoint:** `POST http://localhost:8003/devices/{device_id}/command`

**Function:**
- Validates command format
- Looks up serial port connection for device_id
- Sends command via serial port
- Reads and parses NDJSON response
- Returns structured response

---

### 3. MycoBrain Service → Serial Port

**Library:** `pyserial`

**Function:**
- Opens/manages serial port connections
- Sends UTF-8 encoded JSON commands + newline
- Reads NDJSON responses line-by-line
- Handles timeouts and errors
- Maintains connection state

---

### 4. Serial Port → Firmware

**Firmware Function:**
- Receives commands via UART
- Parses JSON or plaintext commands
- Executes actions (LED, buzzer, I2C, etc.)
- Outputs NDJSON responses
- Sends periodic telemetry

---

## Testing Checklist

### Basic Functionality

- [ ] Board powers on (green LED visible)
- [ ] Serial output visible at 115200 baud
- [ ] No brownout errors
- [ ] No reset loops
- [ ] `status` command responds with NDJSON
- [ ] `mode machine` enables NDJSON output
- [ ] `led red/green/blue/off` commands work
- [ ] `buzzer beep/coin` commands work
- [ ] `scan` command detects I2C devices
- [ ] Telemetry sent every 5-10 seconds in NDJSON format

### Device Manager Integration

- [ ] Device Manager shows available ports
- [ ] Connect button successfully connects to device
- [ ] Device appears in connected devices list
- [ ] Telemetry updates every 5 seconds
- [ ] NeoPixel controls (Red/Green/Blue/Off) work
- [ ] Buzzer controls (Beep/Off) work
- [ ] I2C Scan button works and shows detected devices
- [ ] MOSFET controls toggle correctly
- [ ] Disconnect button properly closes connection

---

## Firmware Requirements for Machine Mode

### Essential Features

1. **NDJSON Output:**
   - All responses must be valid JSON objects
   - One JSON object per line, terminated by `\n`
   - No plaintext output when machine mode is enabled

2. **Command Parsing:**
   - Support both plaintext (`led red`) and JSON (`{"command":"set_neopixel","r":255}`)
   - Return consistent response format

3. **Telemetry Format:**
   - Periodic telemetry in NDJSON format
   - Include all sensor readings
   - Timestamp in each telemetry message

4. **Error Handling:**
   - Invalid commands return error JSON: `{"type":"error","message":"..."}`
   - Successful commands return: `{"type":"response","command":"...","status":"ok"}`

### Example Firmware Code Structure

```cpp
// Pseudo-code for firmware machine mode
bool machine_mode = false;

void handleCommand(String cmd) {
  if (cmd == "mode machine") {
    machine_mode = true;
    sendResponse("mode", "ok", "mode", "machine");
  } else if (cmd == "mode human") {
    machine_mode = false;
    sendResponse("mode", "ok", "mode", "human");
  } else if (cmd.startsWith("led ")) {
    // Parse LED command
    executeLEDCommand(cmd);
    sendResponse("set_neopixel", "ok", "r", r, "g", g, "b", b);
  } else if (cmd.startsWith("buzzer ")) {
    // Parse buzzer command
    executeBuzzerCommand(cmd);
    sendResponse("set_buzzer", "ok", "frequency", freq, "duration", dur);
  }
  // ... other commands
}

void sendResponse(String command, String status, ...) {
  if (machine_mode) {
    // Build JSON object
    String json = "{\"type\":\"response\",\"command\":\"" + command + "\",\"status\":\"" + status + "\"";
    // Add additional fields
    json += "}\n";
    Serial.print(json);
  } else {
    // Plaintext response
    Serial.println("OK: " + command);
  }
}

void sendTelemetry() {
  if (machine_mode) {
    String json = "{\"type\":\"telemetry\",\"timestamp\":" + String(millis()/1000);
    json += ",\"temperature\":" + String(temp);
    json += ",\"humidity\":" + String(humidity);
    json += ",\"pressure\":" + String(pressure);
    json += "}\n";
    Serial.print(json);
  }
}
```

---

## Summary

The Device Manager worked with Machine Mode by:

1. **Connecting** to the MycoBrain board via serial port (COM5/COM6) at 115200 baud
2. **Enabling Machine Mode** by sending `mode machine` command
3. **Sending Commands** as JSON objects via serial port
4. **Receiving Responses** as NDJSON (one JSON object per line)
5. **Polling Telemetry** every 5 seconds and parsing NDJSON telemetry messages
6. **Displaying Data** in the React UI component

The key advantage of Machine Mode is that all communication is structured JSON, making it easy for automated systems to parse and process responses without complex text parsing logic.

---

## Files Reference

- **Device Manager Component:** `components/mycobrain-device-manager.tsx`
- **API Routes:** `app/api/mycobrain/*/route.ts`
- **MycoBrain Service:** `services/mycobrain/mycobrain_service.py` (in website repo)
- **Protocol Spec:** `docs/protocols/MDP_V1_SPEC.md`
- **Integration Guide:** `docs/integrations/MYCOBRAIN_INTEGRATION.md`

---

**Last Updated:** January 6, 2025  
**For:** Firmware debugging agent  
**Context:** MycoBrain board integration with Device Manager using Machine Mode (NDJSON protocol)
