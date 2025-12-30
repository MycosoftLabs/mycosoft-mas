# MycoBrain Advanced Firmware v2.0

**ESP32-S3 based environmental sensing and science communication platform**

## Overview

MycoBrain Advanced is a comprehensive firmware for the Mycosoft MycoBrain ESP32-S3 board. It provides:

- **NeoPixel LED Control** - SK6805 addressable LED on GPIO15
- **Buzzer Patterns** - MOSFET-driven piezo buzzer on GPIO16
- **Optical Modem (LiFi)** - Data transmission via LED for camera/light sensor receivers
- **Acoustic Modem** - FSK data transmission via buzzer for microphone receivers
- **Stimulus Engine** - Controlled light/sound patterns for scientific experiments
- **Peripheral Discovery** - I2C device scanning with auto-identification
- **JSON-CLI Protocol** - Clean machine-readable communication

## Hardware Pin Assignments

| Function | GPIO | Notes |
|----------|------|-------|
| NeoPixel LED | 15 | SK6805 (WS2812-class), RMT driver |
| Buzzer | 16 | MOSFET-driven piezo, LEDC PWM |
| I2C SCL | 4 | 100kHz, 3.3V with pullups |
| I2C SDA | 5 | 100kHz, 3.3V with pullups |
| MOSFET Out 1 | 12 | Digital output, NOT LED |
| MOSFET Out 2 | 13 | Digital output, NOT LED |
| MOSFET Out 3 | 14 | Digital output, NOT LED |
| Analog In 1 | 6 | ADC input |
| Analog In 2 | 7 | ADC input |
| Analog In 3 | 10 | ADC input |
| Analog In 4 | 11 | ADC input |

## Building & Uploading

### Using PlatformIO (Recommended)

```bash
cd firmware/MycoBrain_Advanced
pio run -t upload
pio device monitor -b 115200
```

### Using Arduino IDE

1. Open `src/main.cpp` in Arduino IDE
2. Select board: **ESP32-S3 Dev Module**
3. Configure settings:
   - CPU Frequency: **240 MHz**
   - Flash Mode: **QIO @ 80 MHz**
   - Flash Size: **16 MB**
   - Partition Scheme: **16MB Flash (3MB App / 9.9MB FATFS)**
   - PSRAM: **OPI PSRAM**
   - USB CDC On Boot: **Enabled**
   - USB Mode: **Hardware CDC and JTAG**
4. Upload

## Operating Modes

### Human Mode (Default)
- Verbose output with banners and help text
- Friendly command feedback

### Machine Mode
- Strict NDJSON output (one JSON object per line)
- No ASCII art or decorative output
- All responses are valid JSON

Switch modes:
```
mode machine    # Enable machine mode
mode human      # Enable human mode
```

## Command Reference

### System Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `mode machine\|human` | Switch operating mode |
| `status` | Get full system status (JSON) |
| `dbg on\|off` | Enable/disable debug output |

### LED Control (GPIO15 NeoPixel)

| Command | Description |
|---------|-------------|
| `led rgb <r> <g> <b>` | Set LED color (0-255 each) |
| `led off` | Turn LED off |
| `led status` | Get LED state |

### Buzzer Control (GPIO16)

| Command | Description |
|---------|-------------|
| `buzz tone <hz> <ms>` | Play tone at frequency for duration |
| `buzz pattern <name>` | Play named pattern |
| `buzz stop` | Stop buzzer |

**Available patterns:** `coin`, `bump`, `power`, `1up`, `morgio`, `alert`, `warning`, `success`, `error`

### Optical Modem (LiFi TX)

| Command | Description |
|---------|-------------|
| `optx start {...}` | Start optical data transmission (JSON config) |
| `optx stop` | Stop transmission |
| `optx pattern <name>` | Start visual pattern |
| `optx status` | Get modem status |

**Patterns:** `pulse`, `sweep`, `beacon`, `strobe`

**JSON Config Example:**
```json
{
  "cmd": "optx.start",
  "profile": "camera_manchester",
  "rate_hz": 10,
  "payload_b64": "SGVsbG8gV29ybGQh",
  "repeat": true,
  "rgb": [255, 255, 255],
  "include_crc": true
}
```

### Acoustic Modem (Audio TX)

| Command | Description |
|---------|-------------|
| `aotx start {...}` | Start acoustic data transmission (JSON config) |
| `aotx stop` | Stop transmission |
| `aotx pattern <name>` | Start audio pattern |
| `aotx status` | Get modem status |

**Patterns:** `sweep`, `chirp`, `pulse`, `siren`

**JSON Config Example:**
```json
{
  "cmd": "aotx.start",
  "profile": "simple_fsk",
  "symbol_ms": 30,
  "f0": 1800,
  "f1": 2400,
  "payload_b64": "SGVsbG8gV29ybGQh",
  "repeat": false,
  "include_crc": true
}
```

### Stimulus Engine

| Command | Description |
|---------|-------------|
| `stim light {...}` | Start light stimulus (JSON config) |
| `stim sound {...}` | Start sound stimulus (JSON config) |
| `stim stop` | Stop all stimuli |
| `stim status` | Get stimulus status |

**Light Stimulus JSON:**
```json
{
  "cmd": "stim.light",
  "rgb": [255, 0, 0],
  "on_ms": 500,
  "off_ms": 500,
  "ramp_ms": 100,
  "repeat": 10,
  "delay_ms": 0
}
```

**Sound Stimulus JSON:**
```json
{
  "cmd": "stim.sound",
  "hz": 1000,
  "on_ms": 200,
  "off_ms": 200,
  "sweep_hz": 500,
  "repeat": 5,
  "delay_ms": 1000
}
```

### Peripheral Discovery

| Command | Description |
|---------|-------------|
| `periph scan` | Scan I2C bus |
| `periph list` | List all discovered peripherals |
| `periph describe <uid>` | Get full peripheral descriptor |
| `periph hotplug on\|off` | Enable/disable hotplug detection |

### GPIO Outputs (MOSFET channels)

| Command | Description |
|---------|-------------|
| `out set <1\|2\|3> <0\|1>` | Set output channel high/low |

## NDJSON Protocol

In machine mode, all output is NDJSON (one JSON object per line):

### Response Types

**Acknowledgment:**
```json
{"type":"ack","cmd":"led","r":255,"g":0,"b":0,"ok":true}
```

**Error:**
```json
{"type":"err","cmd":"led","error":"missing argument","ok":false}
```

**Telemetry (periodic):**
```json
{"type":"telemetry","uptime_ms":12345,"led":{"r":255,"g":0,"b":0,"on":true},...}
```

**Status:**
```json
{"type":"status","firmware":"MycoBrain-Advanced","version":"2.0.0",...}
```

**Peripheral:**
```json
{"type":"periph","peripheral_uid":"i2c-...-0x76","peripheral_type":"bme688",...}
```

## Science Communication Features

### Optical Modem (LiFi)

The optical modem uses the NeoPixel LED to transmit data that can be received by:
- Smartphone cameras (5-20 Hz, frame-rate synced)
- Photodiodes/light sensors (up to 60 Hz)
- Other MycoBrain devices with light sensors

**Profiles:**
- `camera_ook` - Simple On-Off Keying, best for cameras
- `camera_manchester` - Manchester encoding, better clock recovery

### Acoustic Modem

The acoustic modem uses the buzzer to transmit data audible to microphones:
- Based on FSK (Frequency Shift Keying)
- Inspired by ggwave/gibberlink protocols
- Includes preamble for synchronization
- CRC16 for error detection

**Profiles:**
- `simple_fsk` - 2-tone FSK with preamble + CRC16

### Stimulus Engine

For scientific experiments with organisms (fungi, plants, insects):
- Precise timing control
- Separate from modem mode (no interference with data protocols)
- Event logging for experiment records
- Synchronized multi-modal stimuli

## Peripheral Descriptor Schema

When a peripheral is discovered, its descriptor includes:

```json
{
  "type": "periph",
  "board_id": "AA:BB:CC:DD:EE:FF",
  "bus": "i2c0",
  "address": "0x76",
  "peripheral_uid": "i2c-AA:BB:CC:DD:EE:FF-0x76",
  "peripheral_type": "bme688",
  "vendor": "Bosch",
  "product": "BME688",
  "revision": "1.0",
  "online": true,
  "capabilities": ["telemetry", "gas_sensing"],
  "data_plane": {
    "control": "i2c",
    "stream": "none"
  },
  "ui_widget": "environmental_sensor"
}
```

This enables the dashboard to auto-generate appropriate UI widgets.

## Known I2C Devices

| Address | Device | Type |
|---------|--------|------|
| 0x76, 0x77 | BME688 | Environmental Sensor |
| 0x44, 0x45 | SHT40/SHT45 | Temp/Humidity |
| 0x23, 0x5C | BH1750 | Light Sensor |
| 0x29 | VL53L0X | ToF Distance |
| 0x3C, 0x3D | OLED Display | Display |
| 0x50, 0x51 | EEPROM | ID Storage |

## Troubleshooting

### LED not working
- Verify GPIO15 is the NeoPixel data pin
- Check NeoPixelBus library is installed
- Try `led rgb 255 0 0` command

### Buzzer not working
- Verify GPIO16 is the buzzer pin
- Check MOSFET driver circuit
- Try `buzz tone 1000 500` command

### Serial communication issues
- Ensure baud rate is 115200
- Check USB CDC on Boot is enabled
- Try different USB cable

### I2C devices not detected
- Verify SCL=GPIO4, SDA=GPIO5
- Check pullup resistors (4.7kΩ typical)
- Run `periph scan` command

## License

Copyright © 2025 Mycosoft. All rights reserved.

