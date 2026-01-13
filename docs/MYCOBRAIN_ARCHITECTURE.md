# MycoBrain Hardware Architecture

**Version**: 2.0.0  
**Date**: 2026-01-10  
**Status**: Active  

---

## Overview

MycoBrain is a dual-MCU ESP32-S3 platform designed for environmental sensing and IoT gateway functionality. The architecture separates **sensor operations (Side-A)** from **communications and routing (Side-B)**, enabling independent firmware development and testing.

---

## Hardware Specifications

### ESP32-S3-WROOM-1 Module

| Specification | Value |
|---------------|-------|
| CPU | Dual-core Xtensa LX7 @ 240MHz |
| RAM | 512KB SRAM + 8MB OPI PSRAM |
| Flash | 16MB Quad SPI |
| WiFi | 2.4GHz 802.11 b/g/n |
| Bluetooth | BLE 5.0 |
| USB | Dual USB-C (CDC + OTG) |

---

## Dual MCU Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         MYCOBRAIN BOARD                                 │
├───────────────────────────────┬────────────────────────────────────────┤
│         SIDE-A (SENSOR)       │         SIDE-B (ROUTER)                │
├───────────────────────────────┼────────────────────────────────────────┤
│                               │                                         │
│  ┌─────────────────────────┐  │  ┌─────────────────────────────────┐   │
│  │     BME688/690          │  │  │       SX1262 LoRa               │   │
│  │   (I2C 0x76/0x77)       │  │  │     915MHz Radio                │   │
│  └────────────┬────────────┘  │  └────────────┬────────────────────┘   │
│               │               │               │                         │
│  ┌─────────────────────────┐  │  ┌─────────────────────────────────┐   │
│  │    BSEC2 AI Engine      │  │  │      Packet Router              │   │
│  │   Smell Classification   │  │  │   LoRa <-> UART <-> WiFi       │   │
│  └────────────┬────────────┘  │  └────────────┬────────────────────┘   │
│               │               │               │                         │
│  ┌─────────────────────────┐  │  ┌─────────────────────────────────┐   │
│  │   Analog Inputs (4)     │  │  │      Command Parser             │   │
│  │   GPIO 6,7,10,11        │  │  │   CLI + MDP Protocol            │   │
│  └────────────┬────────────┘  │  └────────────┬────────────────────┘   │
│               │               │               │                         │
│  ┌─────────────────────────┐  │  ┌─────────────────────────────────┐   │
│  │   MOSFET Outputs (4)    │  │  │      ACK/NACK Handler           │   │
│  │   GPIO 12,13,14         │  │  │   Reliable Delivery             │   │
│  └────────────┬────────────┘  │  └────────────┬────────────────────┘   │
│               │               │               │                         │
│  ┌─────────────────────────┐  │  ┌─────────────────────────────────┐   │
│  │   NeoPixel LED          │  │  │      Optical Modem              │   │
│  │   GPIO 15 (SK6805)      │  │  │   Light-based Data TX           │   │
│  └────────────┬────────────┘  │  └────────────┬────────────────────┘   │
│               │               │               │                         │
│  ┌─────────────────────────┐  │  ┌─────────────────────────────────┐   │
│  │   Buzzer                │  │  │      Acoustic Modem             │   │
│  │   GPIO 16               │  │  │   Sound-based Data TX           │   │
│  └─────────────────────────┘  │  └─────────────────────────────────┘   │
│                               │                                         │
│  USB-C Port 1 (UART0)         │  USB-C Port 2 (UART2/OTG)              │
│  TXD0=GPIO43, RXD0=GPIO44     │  TXD2=GPIO8, RXD2=GPIO9                │
│                               │                                         │
└───────────────────────────────┴────────────────────────────────────────┘
                    │                              │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │      Internal UART Bridge     │
                    │   UART1: TXD1=GPIO17,         │
                    │          RXD1=GPIO18          │
                    └──────────────────────────────┘
```

---

## GPIO Pin Assignments

### Side-A (Sensor MCU)

| GPIO | Function | Description |
|------|----------|-------------|
| 4 | I2C SCL | I2C clock (BME688) |
| 5 | I2C SDA | I2C data (BME688) |
| 6 | ADC1_CH5 | Analog input 1 |
| 7 | ADC1_CH6 | Analog input 2 |
| 10 | ADC1_CH9 | Analog input 3 |
| 11 | ADC2_CH0 | Analog input 4 |
| 12 | MOSFET1 | Output control 1 |
| 13 | MOSFET2 | Output control 2 |
| 14 | MOSFET3 | Output control 3 |
| 15 | NeoPixel | SK6805 addressable LED |
| 16 | Buzzer | Piezo buzzer output |
| 43 | TXD0 | USB-C UART transmit |
| 44 | RXD0 | USB-C UART receive |

### Side-B (Router MCU)

| GPIO | Function | Description |
|------|----------|-------------|
| 8 | TXD2 | UART2 transmit (USB-OTG) |
| 9 | RXD2 | UART2 receive (USB-OTG) |
| 17 | TXD1 | UART1 transmit (internal bridge) |
| 18 | RXD1 | UART1 receive (internal bridge) |
| SPI | SX1262 | LoRa radio interface |

---

## Firmware Variants

### Current Working Firmware

**File**: `firmware/temp_firmware.ino`  
**Status**: Production (as of 2026-01-08)  
**Boards Running**: 1-3 MycoBrain units

#### Features

- Full CLI command interface
- Dual BME688 support (I2C 0x76/0x77)
- BSEC2 smell classification
- MOSFET control
- Analog input reading
- NeoPixel LED control
- Buzzer control
- I2C pin configuration

#### CLI Commands

```
help                - Show all commands
status              - Device status
bme [0|1|both]      - Read BME688 sensor(s)
smell               - Get smell classification
led [r] [g] [b]     - Set LED color (0-255)
buzz [ms]           - Activate buzzer
mosfet [1-4] [on|off] - Control MOSFET output
analog [1-4]        - Read analog input
i2c [sda] [scl] [hz] - Configure I2C pins
scan                - Scan I2C bus
config [key] [value] - Get/set configuration
```

### Side-A Firmware (Planned)

**Purpose**: Dedicated sensor operations

```cpp
// Side-A responsibilities:
// - BME688/690 sensor management
// - BSEC2 AI smell classification
// - Analog input sampling
// - MOSFET output control
// - LED and buzzer feedback
// - Telemetry packaging
// - UART1 communication to Side-B
```

### Side-B Firmware (Planned)

**Purpose**: Gateway and routing operations

```cpp
// Side-B responsibilities:
// - LoRa SX1262 radio management
// - WiFi mesh networking
// - BLE connectivity
// - MQTT publishing
// - HTTP/REST API
// - Optical modem transmission
// - Acoustic modem transmission
// - UART1 communication from Side-A
// - Command routing and ACK handling
```

---

## Communication Protocols

### 1. MDP (MycoBrain Device Protocol)

Binary protocol for efficient sensor data transmission:

```
┌──────┬──────┬──────────┬──────────┬──────┬───────┐
│ SYNC │ LEN  │ MSG_TYPE │ PAYLOAD  │ CRC  │  END  │
│ 0xAA │ 1B   │    1B    │  0-252B  │  2B  │ 0x55  │
└──────┴──────┴──────────┴──────────┴──────┴───────┘
```

### 2. Serial CLI

Human-readable text commands over USB serial:

```
> status
Device: MycoBrain-001
Firmware: 1.0.0
Uptime: 3h 42m
BME688-AMB: 0x77 OK
BME688-ENV: 0x76 OK
WiFi: Connected
LoRa: Standby
```

### 3. REST API (via Side-B WiFi)

```
GET  /api/status         - Device status
GET  /api/sensors        - All sensor readings
GET  /api/bme            - BME688 data
POST /api/mosfet         - Control MOSFET
POST /api/led            - Set LED color
GET  /api/smell          - Smell classification
```

---

## Integration with Website

### Current Implementation

The website communicates with MycoBrain devices via:

1. **Serial over USB**
   - Website → API Route → Node.js SerialPort → MycoBrain
   - File: `/api/mycobrain/[port]/route.ts`

2. **MycoBrain Service**
   - Background service managing device connections
   - Port: 8003
   - File: `services/mycobrain_service.py`

### Data Flow

```
MycoBrain Device
      │
      │ USB Serial (COM3-10)
      ▼
MycoBrain Service (:8003)
      │
      │ REST API
      ▼
Website API (/api/mycobrain)
      │
      │ React Component
      ▼
NatureOS Dashboard
```

---

## Gateway Architecture (Planned)

### Gateway VM Requirements

For production deployment on Proxmox:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| vCPU | 2 | 4 |
| RAM | 4GB | 8GB |
| Storage | 20GB | 50GB |
| USB | Passthrough | Passthrough |

### Gateway Services

```
┌────────────────────────────────────────────────────┐
│              MYCOBRAIN GATEWAY VM                   │
├────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────┐    ┌─────────────────────┐    │
│  │ Serial Manager  │    │   LoRa Gateway      │    │
│  │ (USB Passthru)  │    │   (SX1262 USB)      │    │
│  └────────┬────────┘    └──────────┬──────────┘    │
│           │                        │                │
│           └───────────┬────────────┘                │
│                       │                             │
│           ┌───────────┴───────────┐                 │
│           │   Message Router      │                 │
│           │   (Redis Streams)     │                 │
│           └───────────┬───────────┘                 │
│                       │                             │
│  ┌─────────────────┬──┴──┬─────────────────────┐   │
│  │                 │     │                      │   │
│  ▼                 ▼     ▼                      ▼   │
│  MINDEX API    Website   MQTT      Telemetry DB    │
│  (:8000)       (:3000)   Broker    (TimescaleDB)   │
│                                                     │
└────────────────────────────────────────────────────┘
```

---

## COM Port Management

### Windows COM Port Discovery

```powershell
# List MycoBrain devices
Get-WmiObject Win32_SerialPort | Where-Object { $_.Description -like "*USB*" }

# Or via PowerShell
[System.IO.Ports.SerialPort]::GetPortNames()
```

### Service Conflict Resolution

When developing firmware while the MycoBrain service is running:

1. **Stop the service**:
   ```powershell
   Stop-Process -Name "python" -Force  # If running via Python
   docker stop mycobrain-service        # If running in Docker
   ```

2. **Flash firmware** via Arduino IDE

3. **Restart the service**:
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   python services/mycobrain_service.py
   ```

### Automatic Port Detection

The service uses automatic port detection:

```python
import serial.tools.list_ports

def find_mycobrain_ports():
    ports = []
    for port in serial.tools.list_ports.comports():
        if "USB" in port.description or "ESP32" in port.description:
            ports.append(port.device)
    return ports
```

---

## BSEC2 Integration

### Sensor Configuration

```cpp
// BME688 sensor addresses
#define BME688_AMB_ADDR 0x77  // Ambient sensor
#define BME688_ENV_ADDR 0x76  // Environment sensor

// BSEC configuration
#define BSEC_CONFIG_FILE "bsec_config.bin"
#define BSEC_STATE_FILE  "bsec_state.bin"
```

### Smell Classification Output

```json
{
  "timestamp": 1704931200,
  "gas_index": 127,
  "iaq": 45.2,
  "iaq_accuracy": 3,
  "static_iaq": 42.1,
  "co2_equivalent": 412.5,
  "breath_voc": 0.32,
  "raw_temperature": 23.45,
  "raw_humidity": 45.2,
  "raw_pressure": 101325.0,
  "raw_gas": 125432,
  "class_prediction": "mushroom_agaricus",
  "class_confidence": 0.87
}
```

---

## Optical & Acoustic Modems

### Optical Modem

Uses NeoPixel LED for data transmission:

```cpp
// Optical transmission
void transmit_optical(uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        for (int bit = 7; bit >= 0; bit--) {
            if (data[i] & (1 << bit)) {
                neopixel.setPixelColor(0, 0, 255, 0);  // Green = 1
            } else {
                neopixel.setPixelColor(0, 0, 0, 255);  // Blue = 0
            }
            neopixel.show();
            delayMicroseconds(100);  // 10kbps
        }
    }
}
```

### Acoustic Modem

Uses buzzer for data transmission:

```cpp
// Acoustic transmission (FSK)
#define FREQ_ZERO 1000   // Hz
#define FREQ_ONE  2000   // Hz
#define BIT_TIME  10     // ms

void transmit_acoustic(uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        for (int bit = 7; bit >= 0; bit--) {
            int freq = (data[i] & (1 << bit)) ? FREQ_ONE : FREQ_ZERO;
            tone(BUZZER_PIN, freq, BIT_TIME);
            delay(BIT_TIME);
        }
    }
}
```

---

## Testing Procedures

### 1. Basic Connectivity Test

```powershell
# Connect to device
$port = new-object System.IO.Ports.SerialPort COM5,115200,None,8,one
$port.Open()
$port.WriteLine("status")
Start-Sleep -Seconds 1
$port.ReadExisting()
$port.Close()
```

### 2. Sensor Test

```
> bme both
BME688-AMB (0x77):
  Temperature: 23.45°C
  Humidity: 45.2%
  Pressure: 1013.25 hPa
  Gas: 125432 Ohm

BME688-ENV (0x76):
  Temperature: 24.12°C
  Humidity: 62.1%
  Pressure: 1013.18 hPa
  Gas: 98765 Ohm
```

### 3. Smell Training Test

```
> smell
Classification: mushroom_agaricus
Confidence: 87.3%
IAQ: 45.2 (Good)
```

---

## Related Documents

- [BME688_INTEGRATION_COMPLETE_2026-01-09.md](./BME688_INTEGRATION_COMPLETE_2026-01-09.md)
- [OPTICAL_ACOUSTIC_MODEM_INTEGRATION_2026-01-09.md](./OPTICAL_ACOUSTIC_MODEM_INTEGRATION_2026-01-09.md)
- [MINDEX_SMELL_TRAINING_SYSTEM.md](./MINDEX_SMELL_TRAINING_SYSTEM.md)
- [MYCOBRAIN_COM_PORT_MANAGEMENT.md](./MYCOBRAIN_COM_PORT_MANAGEMENT.md)
- [PROXMOX_DEPLOYMENT.md](./PROXMOX_DEPLOYMENT.md)

---

*Last Updated: 2026-01-10 v2.0*
