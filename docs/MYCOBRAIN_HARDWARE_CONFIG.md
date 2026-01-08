# MycoBrain ESP32-S3 Hardware Configuration

## Arduino IDE Settings

| Setting | Value |
|---------|-------|
| **Board** | ESP32S3 Dev Module |
| **ESP32 Board Version** | 2.0.13 |
| **USB CDC on Boot** | Enabled |
| **USB DFU on Boot** | Enabled (requires USB-OTG Mode) |
| **USB Mode** | UART0 / Hardware CDC |
| **JTAG Adapter** | Integrated USB JTAG |
| **PSRAM** | OPI PSRAM |
| **CPU Frequency** | 240 MHz (WiFi) |
| **Flash Mode** | QIO @ 80 MHz |
| **Flash Size** | 16 MB (128 Mb) |
| **Partition Scheme** | 16MB flash, 3MB app / 9.9MB FATFS |
| **Upload Speed** | 921600 |

---

## Hardware Pin Configuration

### Core I/O Pins

| Function | GPIO Pin | Notes |
|----------|----------|-------|
| **I2C SCL** | GPIO 4 | BSEC/BME688 sensors |
| **I2C SDA** | GPIO 5 | BSEC/BME688 sensors |
| **NeoPixel LED** | GPIO 15 | SK6805 addressable RGB (single LED) |
| **Buzzer** | GPIO 16 | PWM passive buzzer |

### Analog Input Pins

| Function | GPIO Pin |
|----------|----------|
| Analog In 1 | GPIO 6 |
| Analog In 2 | GPIO 7 |
| Analog In 3 | GPIO 10 |
| Analog In 4 | GPIO 11 |

### MOSFET Output Pins (3.3V Switching)

| Function | GPIO Pin |
|----------|----------|
| MOSFET Out 1 | GPIO 12 |
| MOSFET Out 2 | GPIO 13 |
| MOSFET Out 3 | GPIO 14 |

### Serial Communication Pins

| Function | TX GPIO | RX GPIO |
|----------|---------|---------|
| UART0 | GPIO 43 | GPIO 44 |
| UART1 | GPIO 17 | GPIO 18 |
| UART2 | GPIO 8 | GPIO 9 |

---

## BME688 Dual Sensor Configuration

### I2C Address Setup

The board supports TWO BME688 sensors with different I2C addresses:

| Sensor | I2C Address | Purpose |
|--------|-------------|---------|
| **AMB** (Ambient) | 0x77 | Primary sensor |
| **ENV** (Environment) | 0x76 | Secondary sensor |

### Important Notes

1. **Solder Bridge Required**: Each BME688 has a solder bridge/jumper to change its I2C address
2. **Address Conflict**: Without the solder modification, both sensors would be at the same address (0x77) and the board WILL NOT WORK
3. **BSEC Library**: The Bosch BSEC2 library requires separate instances per sensor with separate memory/state buffers

### I2C Pin Flipping

If SDA/SCL are swapped during hardware assembly, the firmware supports pin reconfiguration:

```
CLI Command: i2c <sda> <scl> [hz]
Example: i2c 5 4 100000   (default configuration)
Example: i2c 4 5 100000   (flipped SDA/SCL)
```

---

## LoRa Module Pinout (Alternative Configuration)

For boards with LoRa SX1262 module instead of sensors:

| Function | GPIO Pin |
|----------|----------|
| SX RESET | GPIO 7 |
| SX BUSY | GPIO 8 |
| SX CS | GPIO 9 |
| SX CLK | GPIO 10 |
| SX MISO | GPIO 11 |
| SX MOSI | GPIO 12 |
| SX DIO1 | GPIO 13 |
| SX DIO2 | GPIO 14 |
| NeoPixel | GPIO 15 |

---

## LED Color Codes

The SK6805 NeoPixel uses standard RGB color codes:

| Color | Code | RGB Values |
|-------|------|------------|
| BLACK | 0 | (0, 0, 0) |
| RED | 1 | (255, 0, 0) |
| GREEN | 2 | (0, 255, 0) |
| BLUE | 3 | (0, 0, 255) |
| WHITE | 4 | (255, 255, 255) |
| ORANGE | 5 | (255, 121, 0) |
| YELLOW | 6 | (255, 255, 0) |
| VIOLET | 7 | (143, 0, 255) |
| PINK | 8 | (255, 20, 147) |

### LED State Indicators (Firmware)

| Color | Meaning |
|-------|---------|
| GREEN | Both sensors initialized + subscription OK |
| YELLOW | Sensors OK but subscription failed |
| BLUE | Initializing / waiting for first valid readings |
| RED | No sensors detected or begin failed |

---

## Firmware CLI Commands

The firmware supports a text-based CLI interface at 115200 baud:

### General Commands

| Command | Description |
|---------|-------------|
| `help` | Display available commands |
| `poster` | Reprint SuperMorgIO POST screen |
| `status` | Show initialization stages + current readings |

### I2C Commands

| Command | Description |
|---------|-------------|
| `scan` | Perform I2C bus scan |
| `i2c <sda> <scl> [hz]` | Set I2C pins and clock speed |

### Sensor Commands

| Command | Description |
|---------|-------------|
| `probe amb\|env [n]` | Read chip/variant ID (n times) |
| `regs amb\|env` | Read chip/variant ID once |
| `rate amb\|env lp\|ulp` | Set sample rate (Low Power/Ultra Low Power) |

### LED Commands

| Command | Description |
|---------|-------------|
| `led mode off\|state\|manual` | Set LED indicator mode |
| `led rgb <r> <g> <b>` | Set manual RGB color (0-255) |

### Output Commands

| Command | Description |
|---------|-------------|
| `live on\|off` | Toggle periodic live output |
| `dbg on\|off` | Toggle debug prints |
| `fmt lines\|json` | Set output format (human readable or NDJSON) |

### Sound Effects

| Command | Description |
|---------|-------------|
| `morgio` | Play SuperMorgIO boot jingle |
| `coin` | Play coin SFX |
| `bump` | Play bump SFX |
| `power` | Play power-up SFX |
| `1up` | Play 1-Up SFX |

---

## Required Libraries

```
- Arduino Core for ESP32 (v2.0.13)
- Adafruit NeoPixel OR FastLED
- Bosch BSEC2 Library
- Bosch BME68x Library
- Wire (I2C)
```

---

## Original Sample Code Location

```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\MYCOBRAIN\MYCOSOFT_SampleCode.ino
```

## Full Firmware Location

```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\firmware\MycoBrain_NeoPixel_Fixed\MycoBrain_NeoPixel_Fixed.ino
```

---

## Troubleshooting

### Board not detected in Device Manager

1. Check USB cable (must be data cable, not charge-only)
2. Try different USB port
3. Install ESP32-S3 USB drivers if needed

### No serial response

1. Verify correct baud rate (115200)
2. Check if firmware is uploaded
3. Wait for boot sequence (~2 seconds)

### BME688 sensors not detected

1. Run `scan` command to check I2C devices
2. Try `i2c 4 5` or `i2c 5 4` to flip SDA/SCL
3. Verify solder bridges on BME688 modules for address selection

### Wrong I2C address

1. Ensure one BME688 is modified to use 0x76
2. Default BME688 address is 0x77
3. Solder jumper changes address to 0x76
