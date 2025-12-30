# MycoBrain Advanced Firmware - API Reference

## Communication Protocol

### Serial Configuration
- **Baud Rate:** 115200
- **Data Bits:** 8
- **Stop Bits:** 1
- **Parity:** None
- **Line Ending:** `\n` (LF)

### Message Format

#### Input (Commands)
Commands can be sent in two formats:

**1. Plaintext (CLI-style):**
```
led rgb 255 0 0
buzz pattern coin
status
```

**2. JSON:**
```json
{"cmd":"led.rgb","r":255,"g":0,"b":0}
{"cmd":"buzz.pattern","name":"coin"}
```

The firmware auto-detects the format by checking if the line starts with `{`.

#### Output (Responses)
In **machine mode**, all output is NDJSON (Newline-Delimited JSON):
```json
{"type":"ack","cmd":"led","ok":true}
{"type":"telemetry","uptime_ms":12345,...}
```

In **human mode**, output includes ASCII banners and readable text.

---

## Command Categories

### 1. System Commands

#### `help`
Display available commands.

**Response (machine mode):**
```json
{"type":"help","commands":["help","mode","status","dbg","led",...]}
```

#### `mode <human|machine>`
Switch operating mode.

| Mode | Description |
|------|-------------|
| `human` | Verbose output, banners, help text |
| `machine` | Strict NDJSON, no decorative output |

**Example:**
```
mode machine
```

**Response:**
```json
{"type":"ack","cmd":"mode","msg":"machine mode enabled","ok":true}
```

#### `status`
Get comprehensive system status.

**Response:**
```json
{
  "type": "status",
  "firmware": "MycoBrain-Advanced",
  "version": "2.0.0",
  "uptime_ms": 123456,
  "mode": "machine",
  "debug": false,
  "led": {"r": 0, "g": 0, "b": 0, "on": false},
  "buzzer": {"playing": false},
  "optx": {"active": false, "pattern": false},
  "aotx": {"active": false, "pattern": false},
  "peripherals": 2
}
```

#### `dbg <on|off>`
Enable/disable debug output.

**Example:**
```
dbg on
```

---

### 2. LED Control (NeoPixel)

#### `led rgb <r> <g> <b>`
Set LED color.

| Parameter | Range | Description |
|-----------|-------|-------------|
| `r` | 0-255 | Red intensity |
| `g` | 0-255 | Green intensity |
| `b` | 0-255 | Blue intensity |

**Example:**
```
led rgb 255 128 0
```

**Response:**
```json
{"type":"ack","cmd":"led","r":255,"g":128,"b":0}
```

**JSON Format:**
```json
{"cmd":"led.rgb","r":255,"g":128,"b":0}
```

#### `led off`
Turn LED off.

#### `led status`
Get current LED state.

**Response:**
```json
{"type":"status","cmd":"led","r":255,"g":128,"b":0,"on":true}
```

---

### 3. Buzzer Control

#### `buzz tone <hz> <ms>`
Play a tone.

| Parameter | Range | Description |
|-----------|-------|-------------|
| `hz` | 20-20000 | Frequency in Hertz |
| `ms` | 0-65535 | Duration in milliseconds |

**Example:**
```
buzz tone 1000 500
```

#### `buzz pattern <name>`
Play a predefined pattern.

| Pattern | Description |
|---------|-------------|
| `coin` | Mario coin sound |
| `bump` | Mario bump sound |
| `power` | Power-up melody |
| `1up` | 1-UP sound |
| `morgio` | Morgio jingle |
| `alert` | Alert beeps |
| `warning` | Warning tone (loops) |
| `success` | Success melody |
| `error` | Error buzz |

**Example:**
```
buzz pattern morgio
```

**JSON Format:**
```json
{"cmd":"buzz.pattern","name":"morgio"}
```

#### `buzz stop`
Stop any playing sound.

---

### 4. Optical Modem (LiFi TX)

#### `optx start <config>`
Start optical data transmission.

**JSON Configuration:**
```json
{
  "cmd": "optx.start",
  "profile": "camera_manchester",
  "rate_hz": 10,
  "payload_b64": "SGVsbG8gV29ybGQh",
  "repeat": false,
  "rgb": [255, 255, 255],
  "include_crc": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `profile` | string | `camera_ook`, `camera_manchester` |
| `rate_hz` | number | Symbol rate (5-60 Hz) |
| `payload_b64` | string | Base64-encoded data |
| `repeat` | boolean | Loop transmission |
| `rgb` | array | LED color [r, g, b] |
| `include_crc` | boolean | Append CRC16 to payload |

**Profiles:**

| Profile | Description | Best For |
|---------|-------------|----------|
| `camera_ook` | On-Off Keying | Cameras at 5-20 Hz |
| `camera_manchester` | Manchester encoding | Better sync recovery |

#### `optx stop`
Stop transmission.

#### `optx pattern <name>`
Start a visual pattern (non-data).

| Pattern | Description |
|---------|-------------|
| `pulse` | Slow pulse/breathing |
| `sweep` | Rainbow color sweep |
| `beacon` | Periodic flash |
| `strobe` | Fast strobe |

#### `optx status`
Get modem status.

**Response:**
```json
{
  "type": "status",
  "cmd": "optx",
  "tx_active": true,
  "pattern_active": false,
  "rate_hz": 10
}
```

---

### 5. Acoustic Modem (Audio TX)

#### `aotx start <config>`
Start acoustic data transmission.

**JSON Configuration:**
```json
{
  "cmd": "aotx.start",
  "profile": "simple_fsk",
  "symbol_ms": 30,
  "f0": 1800,
  "f1": 2400,
  "payload_b64": "SGVsbG8gV29ybGQh",
  "repeat": false,
  "include_crc": true,
  "preamble_ms": 200
}
```

| Field | Type | Description |
|-------|------|-------------|
| `profile` | string | `simple_fsk` |
| `symbol_ms` | number | Symbol duration (20-100 ms) |
| `f0` | number | Frequency for bit 0 (Hz) |
| `f1` | number | Frequency for bit 1 (Hz) |
| `payload_b64` | string | Base64-encoded data |
| `repeat` | boolean | Loop transmission |
| `include_crc` | boolean | Append CRC16 |
| `preamble_ms` | number | Preamble duration |

#### `aotx stop`
Stop transmission.

#### `aotx pattern <name>`
Start an audio pattern (non-data).

| Pattern | Description |
|---------|-------------|
| `sweep` | Frequency sweep |
| `chirp` | Logarithmic chirp |
| `pulse` | Pulsed tone |
| `siren` | Alternating tones |

#### `aotx status`
Get modem status.

---

### 6. Stimulus Engine

#### `stim light <config>`
Start light stimulus for experiments.

**JSON Configuration:**
```json
{
  "cmd": "stim.light",
  "rgb": [255, 0, 0],
  "on_ms": 500,
  "off_ms": 500,
  "ramp_ms": 100,
  "repeat": 10,
  "delay_ms": 1000
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rgb` | array | LED color [r, g, b] |
| `on_ms` | number | LED on duration |
| `off_ms` | number | LED off duration |
| `ramp_ms` | number | Fade in/out time (0 = instant) |
| `repeat` | number | Cycle count (0 = infinite) |
| `delay_ms` | number | Initial delay |

#### `stim sound <config>`
Start sound stimulus.

**JSON Configuration:**
```json
{
  "cmd": "stim.sound",
  "hz": 1000,
  "on_ms": 200,
  "off_ms": 200,
  "sweep_hz": 500,
  "repeat": 5,
  "delay_ms": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hz` | number | Base frequency |
| `on_ms` | number | Tone on duration |
| `off_ms` | number | Silence duration |
| `sweep_hz` | number | Frequency modulation range |
| `repeat` | number | Cycle count (0 = infinite) |
| `delay_ms` | number | Initial delay |

#### `stim stop`
Stop all stimuli.

#### `stim status`
Get stimulus status.

**Response:**
```json
{
  "type": "status",
  "cmd": "stim",
  "light_active": true,
  "sound_active": false,
  "elapsed_ms": 5000,
  "cycles": 5
}
```

---

### 7. Peripheral Discovery

#### `periph scan`
Scan I2C bus for devices.

**Response:**
```json
{"type":"ack","cmd":"periph","msg":"scan complete","ok":true}
```

#### `periph list`
List all discovered peripherals.

**Response:**
```json
{
  "type": "periph_list",
  "board_id": "AA:BB:CC:DD:EE:FF",
  "count": 2,
  "peripherals": [
    {
      "address": 118,
      "uid": "i2c-AA:BB:CC:DD:EE:FF-0x76",
      "type": "bme688",
      "product": "BME688",
      "online": true
    },
    {
      "address": 60,
      "uid": "i2c-AA:BB:CC:DD:EE:FF-0x3C",
      "type": "unknown",
      "product": "OLED-128x64",
      "online": true
    }
  ]
}
```

#### `periph describe <uid>`
Get full peripheral descriptor.

**Response:**
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

#### `periph hotplug <on|off>`
Enable/disable automatic hotplug detection.

---

### 8. GPIO Outputs

#### `out set <channel> <value>`
Set MOSFET output channel.

| Parameter | Values | Description |
|-----------|--------|-------------|
| `channel` | 1, 2, 3 | Output channel (GPIO12, 13, 14) |
| `value` | 0, 1 | Low or High |

**Example:**
```
out set 1 1
```

**Response:**
```json
{"type":"ack","cmd":"out","channel":1,"value":1}
```

---

## Telemetry

In machine mode, telemetry is automatically emitted every second:

```json
{
  "type": "telemetry",
  "uptime_ms": 12345678,
  "led": {"r": 0, "g": 255, "b": 0, "on": true},
  "optx_active": false,
  "aotx_active": false,
  "stim_active": true,
  "periph_count": 2
}
```

---

## Error Handling

Errors are returned as:

```json
{
  "type": "err",
  "cmd": "led",
  "error": "missing argument: rgb values required",
  "ok": false
}
```

---

## CRC16 Implementation

The firmware uses CRC16-CCITT for data integrity:
- Polynomial: 0x1021
- Initial value: 0xFFFF
- Applied to payloads before transmission

---

## Base64 Encoding

Payloads in modem commands use standard Base64 encoding:
- Alphabet: `A-Za-z0-9+/`
- Padding: `=`

**Example:**
- Text: `Hello World!`
- Base64: `SGVsbG8gV29ybGQh`

