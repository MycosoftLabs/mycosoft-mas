# MycoBrain ESP32-S3 Device

**Version**: 1.0  
**Hardware**: Dual ESP32-S3 with LoRa, BME688 sensors, NeoPixel, Buzzer  
**Status**: ⚠️ Firmware Recovery Required

---

## Overview

MycoBrain is a modular, dual-ESP32-S3 environmental monitoring and control device designed for mycology research, mushroom cultivation, and environmental data collection. It features dual BME688 gas sensors, addressable NeoPixel LED, piezo buzzer, MOSFET outputs, and LoRa communication.

### Key Features
- **Dual BME688 Sensors** - Temperature, humidity, pressure, gas resistance, IAQ
- **NeoPixel LED** - SK6805 addressable RGB LED (GPIO15)
- **Piezo Buzzer** - Sound effects and alerts (GPIO16)
- **4x MOSFET Outputs** - Control heaters, fans, pumps (GPIO12/13/14)
- **I2C Bus** - Sensor expansion (GPIO4/5)
- **4x Analog Inputs** - ESP32-S3 specific (GPIO6/7/10/11)
- **LoRa Module** - SX1262 for long-range communication
- **Dual MCU Design** - Side-A (sensors) + Side-B (router)

---

## Hardware Specifications

### ESP32-S3 Configuration
- **MCU**: ESP32-S3 (dual-core Xtensa LX7 @ 240MHz)
- **Flash**: 16MB QIO @ 80MHz
- **PSRAM**: 8MB OPI ⚠️ **DO NOT ENABLE IN FIRMWARE**
- **USB**: Hardware CDC (USB Serial)
- **Power**: 5V via USB-C
- **Crystal**: 40MHz

### Pin Mapping

| GPIO | Function | Type | Notes |
|------|----------|------|-------|
| 4 | I2C SCL | I2C | 100kHz, sensor bus |
| 5 | I2C SDA | I2C | 100kHz, sensor bus |
| 6 | AI1 | Analog | ESP32-S3 specific |
| 7 | AI2 | Analog | ESP32-S3 specific |
| 10 | AI3 | Analog | ESP32-S3 specific |
| 11 | AI4 | Analog | ESP32-S3 specific |
| 12 | MOSFET 1 | PWM | External control |
| 13 | MOSFET 2 | PWM | External control |
| 14 | MOSFET 3 | PWM | External control |
| **15** | **NeoPixel** | **SK6805** | **Addressable RGB** |
| **16** | **Buzzer** | **PWM** | **Piezo via MOSFET** |

⚠️ **CRITICAL**: GPIO15 is an SK6805 NeoPixel (WS2812-compatible), NOT a simple LED. Requires NeoPixelBus or FastLED library.

---

## Firmware Versions

### Working Firmware (December 28-30, 2025)

#### 1. MycoBrain_SideA_DualMode ✅ **RECOMMENDED**
- **Features**: Dual mode (CLI + JSON), Machine Mode, NeoPixel, Buzzer, BME688
- **Commands**: `led rgb`, `coin`, `bump`, `power`, `1up`, `morgio`, `status`, `scan`
- **Location**: `firmware/MycoBrain_SideA_DualMode/`
- **Status**: Was working before ScienceComms upgrade

#### 2. MycoBrain_NeoPixel_Fixed ✅
- **Features**: Fixed NeoPixel support (SK6812/FastLED), Buzzer, BSEC2
- **Location**: `firmware/MycoBrain_NeoPixel_Fixed/`
- **Status**: Was working, code fixes applied

#### 3. MycoBrain_Minimal_PIO ✅
- **Features**: Minimal firmware, Buzzer, Serial, NO PSRAM
- **Location**: `firmware/MycoBrain_Minimal_PIO/`
- **Status**: Was working on COM7 (Jan 6, 2026)

#### 4. MycoBrain_ScienceComms ❌ **DO NOT USE**
- **Status**: Causes firmware crashes and boot loops
- **Location**: `firmware/MycoBrain_ScienceComms/`
- **Issue**: NeoPixelBus incompatibility, reset loop

---

## Flashing Firmware

### Prerequisites
- Python 3.x with `esptool` installed
- Arduino IDE 1.8.x or 2.x (for compilation)
- USB-C cable (data-capable)
- Windows: COM port drivers installed

### Method 1: Using Pre-Compiled Binaries (Quick)

**⚠️ IMPORTANT**: Pre-compiled binaries may not work. Use Method 2 if boards don't respond.

```powershell
# Put board in bootloader mode (hold BOOT, press RESET, release BOOT)

# Erase flash
python -m esptool --chip esp32s3 --port COM5 --baud 921600 erase_flash

# Flash complete image
cd firmware/MycoBrain_SideA_DualMode/build/esp32.esp32.esp32s3
python -m esptool --chip esp32s3 --port COM5 --baud 921600 write_flash \
    0x0 MycoBrain_SideA_DualMode.ino.bootloader.bin \
    0x8000 MycoBrain_SideA_DualMode.ino.partitions.bin \
    0x10000 MycoBrain_SideA_DualMode.ino.bin
```

### Method 2: Compile with Arduino IDE (Recommended)

**Step 1: Configure Arduino IDE**
1. Open Arduino IDE
2. File → Preferences → Additional Board Manager URLs:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Tools → Board → Boards Manager → Search "ESP32" → Install "esp32 by Espressif Systems"

**Step 2: Open Firmware**
1. File → Open
2. Navigate to: `firmware/MycoBrain_SideA_DualMode/MycoBrain_SideA_DualMode.ino`
3. Click Open

**Step 3: Configure Board Settings** ⚠️ **CRITICAL**
```
Board: ESP32S3 Dev Module
USB CDC on boot: Enabled ✅
USB DFU on boot: Enabled
USB Firmware MSC on boot: Disabled
USB Mode: Hardware CDC and JTAG ✅
JTAG Adapter: Integrated USB JTAG
PSRAM: Disabled ⚠️ (or OPI PSRAM - test both)
CPU Frequency: 240 MHz
WiFi Core Debug Level: None
Arduino runs on core: 1
Events run on core: 1
Flash Mode: QIO @ 80 MHz ✅
Flash Size: 16 MB ✅
Partition Scheme: 16MB flash, 3MB app / 9.9MB FATFS ✅
Upload Speed: 921600
Upload Port: COM5 (your device port)
```

**Step 4: Compile**
1. Click **Verify** button (✓)
2. Wait for compilation to complete
3. Note the build folder location (shown in output)

**Step 5: Flash with esptool**
```powershell
cd firmware/MycoBrain_SideA_DualMode/build/esp32.esp32.esp32s3

python -m esptool --chip esp32s3 --port COM5 --baud 921600 erase_flash

python -m esptool --chip esp32s3 --port COM5 --baud 921600 write_flash \
    0x0 MycoBrain_SideA_DualMode.ino.bootloader.bin \
    0x8000 MycoBrain_SideA_DualMode.ino.partitions.bin \
    0x10000 MycoBrain_SideA_DualMode.ino.bin
```

**Step 6: Verify**
1. Press RESET button on board
2. Check for:
   - ✅ NeoPixel turns ON (green or color)
   - ✅ Startup jingle plays (3 beeps)
   - ✅ Serial output in Serial Monitor (115200 baud)

---

## Testing Firmware

### Serial Monitor Test
1. Open Serial Monitor (Tools → Serial Monitor)
2. Set baud rate to **115200**
3. Send commands:
   ```
   help
   status
   scan
   led rgb 255 0 0
   coin
   ```
4. Verify responses

### Physical Test
1. **NeoPixel**: Should turn ON after boot
2. **Buzzer**: Send `coin` command, should hear sound
3. **Serial**: Should see boot messages and command responses

---

## Firmware Commands

### LED Control
```
led rgb <r> <g> <b>    - Set NeoPixel color (0-255 each)
led mode off           - Turn off LED
led mode state         - Auto state-based color
led mode manual        - Manual control
```

### Buzzer Sounds
```
coin      - Coin pickup sound
bump      - Bump sound
power     - Power-up sound
1up       - Extra life sound
morgio    - Morg.io sound
```

### Device Info
```
help      - Show all commands
status    - Device info and sensor readings
scan      - I2C bus scan
```

### Machine Mode (for Device Manager)
```
mode machine    - Enable Machine Mode (NDJSON output)
dbg off         - Disable debug prints
fmt json        - JSON output format
```

---

## Integration with Mycosoft MAS

### Service Architecture
```
Website (Port 3000)
  ↓ HTTP REST API
MycoBrain Service (Port 8003)
  ↓ Serial (115200 baud)
MycoBrain ESP32-S3 (COM5/COM7)
```

### Starting the Service
```powershell
cd services/mycobrain
python mycobrain_service_standalone.py
```

Service runs on **http://localhost:8003**

### API Endpoints
```
GET  /health                           - Service health
GET  /devices                          - List devices
GET  /ports                            - Scan COM ports
POST /devices/connect/{port}           - Connect device
GET  /devices/{device_id}/telemetry   - Get telemetry
POST /devices/{device_id}/command      - Send command
```

### Device Manager UI
Navigate to: **http://localhost:3000/natureos/devices**

Features:
- Real-time telemetry display
- NeoPixel color controls
- Buzzer preset buttons
- I2C peripheral scanning
- Sensor data visualization

---

## Troubleshooting

### Issue: No LED or Buzzer Activity

**Symptoms**: Board appears to boot but no LED or sound

**Possible Causes**:
1. Firmware crashes at entry point
2. Wrong bootloader/partition combination
3. PSRAM flags enabled (causes crashes)
4. USB CDC configuration issue

**Solutions**:
1. Compile with Arduino IDE using exact settings
2. Ensure PSRAM is **Disabled** in board settings
3. Flash complete image (bootloader + partitions + firmware)
4. Test with minimal firmware first

### Issue: Continuous Boot Loop

**Symptoms**:
```
ESP-ROM:esp32s3-20210327
rst:0x3 (RTC_SW_SYS_RST)
entry 0x403c98d0
[repeats]
```

**Causes**:
- Firmware compiled with wrong settings
- PSRAM flags enabled
- Bootloader/partition mismatch

**Solution**: Recompile with Arduino IDE, PSRAM **Disabled**

### Issue: Brownout Detector Triggered

**Symptoms**:
```
E BOD: Brownout detector was triggered
```

**Causes**:
- PSRAM flags enabled in firmware
- Insufficient power (rare with USB)
- Wrong bootloader

**Solution**:
1. Remove PSRAM flags from platformio.ini
2. Use NOPSRAM bootloader
3. Recompile firmware

### Issue: No Serial Output

**Symptoms**: Board boots but no serial output

**Causes**:
- Wrong baud rate (should be 115200)
- USB CDC not initialized
- Firmware crashes before Serial.begin()

**Solution**:
1. Check baud rate in Serial Monitor
2. Verify USB CDC on boot is **Enabled**
3. Recompile with correct settings

---

## Development

### Repository Structure
```
firmware/
  ├── MycoBrain_SideA_DualMode/      # Recommended firmware
  ├── MycoBrain_NeoPixel_Fixed/      # NeoPixel fixed version
  ├── MycoBrain_Minimal_PIO/         # Minimal test firmware
  └── MycoBrain_ScienceComms/        # ❌ Do not use

services/
  └── mycobrain/                     # MycoBrain service (port 8003)

components/
  └── mycobrain-device-manager.tsx   # Device Manager UI

docs/
  └── integrations/
      └── MYCOBRAIN_INTEGRATION.md   # Complete integration guide
```

### Building from Source

**PlatformIO** (May not work - use Arduino IDE):
```powershell
cd firmware/MycoBrain_SideA_DualMode
pio run
pio run -t upload --upload-port COM5
```

**Arduino IDE** (Recommended):
1. Open `.ino` file
2. Configure board settings (see Flashing Firmware section)
3. Click Verify/Compile
4. Use esptool to flash binaries

---

## API Reference

### Device Manager API

**Base URL**: `http://localhost:8003`

#### List Devices
```http
GET /devices
```

**Response**:
```json
{
  "devices": [
    {
      "device_id": "mycobrain-side-a-COM5",
      "port": "COM5",
      "side": "side-a",
      "status": "connected",
      "mac_address": "10:B4:1D:E3:3B:88"
    }
  ]
}
```

#### Send Command
```http
POST /devices/{device_id}/command
Content-Type: application/json

{
  "command": {
    "command_type": "set_neopixel",
    "r": 255,
    "g": 0,
    "b": 0
  }
}
```

#### Get Telemetry
```http
GET /devices/{device_id}/telemetry
```

**Response**:
```json
{
  "device_id": "mycobrain-side-a-COM5",
  "timestamp": "2026-01-16T10:30:00Z",
  "sensors": {
    "bme688_0x76": {
      "temperature": 25.5,
      "humidity": 60.2,
      "pressure": 1013.25,
      "gas_resistance": 125000
    }
  }
}
```

---

## Machine Mode Protocol

Machine Mode enables NDJSON (Newline-Delimited JSON) output for automated parsing.

### Initialization Sequence
```
mode machine    # Enable Machine Mode
dbg off         # Disable debug prints
fmt json        # Set JSON output format
scan            # Trigger I2C scan
```

### NDJSON Output Format
```json
{"type":"telemetry","sensor":"AMB","addr":"0x77","tC":25.5,"rh":60.2,"p_hPa":1013.25}
{"type":"telemetry","sensor":"ENV","addr":"0x76","tC":25.3,"rh":59.8,"p_hPa":1013.20}
{"type":"periph","addr":"0x76","name":"BME688"}
{"type":"periph","addr":"0x77","name":"BME688"}
```

---

## Known Issues

### Current Critical Issue (January 16, 2026)

**Problem**: Both boards experiencing firmware boot loop after flashing attempts

**Symptoms**:
- No LED activity
- No buzzer sound
- Firmware crashes at entry point `0x403c98d0`
- Continuous reset loop

**Root Cause**: Firmware compiled with incompatible settings (PSRAM flags, wrong bootloader, USB CDC configuration)

**Solution Required**: Compile with Arduino IDE using exact settings (see Flashing Firmware section)

### Historical Issues (Resolved)

#### PSRAM Brownout (December 2025)
- **Problem**: Firmware with PSRAM flags caused brownout
- **Solution**: Disable PSRAM in firmware compilation
- **Status**: ✅ Resolved

#### NeoPixel Not Working (December 2025)
- **Problem**: Using `digitalWrite()` on GPIO15
- **Solution**: Use NeoPixelBus or FastLED library
- **Status**: ✅ Fixed in code

---

## Contributing

### Code Fixes Applied

**1. BSEC2 Callback Signature** (MycoBrain_NeoPixel_Fixed)
```cpp
// Before (wrong):
static void cbAMB(const bme68xData data, const bsecOutputs outputs, const Bsec2 /*bsec*/)

// After (correct):
static void cbAMB(const bme68xData data, const bsecOutputs outputs, Bsec2 bsec)
```

**2. FastLED LED Type** (MycoBrain_NeoPixel_Fixed)
```cpp
// Before (wrong):
FastLED.addLeds<WS2812B, NEOPIXEL_PIN, GRB>(leds, PIXEL_COUNT);

// After (correct):
FastLED.addLeds<SK6812, NEOPIXEL_PIN, GRB>(leds, PIXEL_COUNT);
```

**3. SensorSlot Initialization** (MycoBrain_NeoPixel_Fixed)
```cpp
// Before (wrong):
static SensorSlot S_AMB = { "AMB", 0x77 };

// After (correct):
static SensorSlot S_AMB;
// Then in setup():
S_AMB.name = "AMB";
S_AMB.addr = 0x77;
```

**4. Wire Re-initialization** (MycoBrain_NeoPixel_Fixed)
```cpp
// Before:
Wire.end();
Wire.begin(gSda, gScl);

// After:
Wire.end();
delay(10);  // Allow I2C bus to stabilize
Wire.begin(gSda, gScl);
```

---

## License

MIT License - See LICENSE file for details

---

## Support

- **Documentation**: `docs/integrations/MYCOBRAIN_INTEGRATION.md`
- **Quick Start**: `MYCOBRAIN_QUICKSTART.md`
- **Status Reports**: `MYCOBRAIN_STATUS_FINAL.md`
- **GitHub**: https://github.com/MycosoftLabs/mycosoft-mas

---

## Changelog

### January 16, 2026
- ⚠️ **CRITICAL**: Firmware boot loop issue on both boards
- Applied code fixes to NeoPixel_Fixed firmware
- Removed PSRAM flags from ScienceComms
- Documented complete system architecture
- Created comprehensive README

### January 6, 2026
- ✅ MycoBrain_Minimal_PIO working on COM7
- ✅ Buzzer confirmed working
- ✅ Serial communication established
- ⚠️ NeoPixel not responding (GPIO pin mismatch)

### December 30, 2025
- ❌ ScienceComms firmware caused boot loops
- ❌ NeoPixelBus incompatibility identified

### December 29, 2025
- ✅ DualMode firmware working
- ✅ Machine Mode operational
- ✅ Device Manager integration complete
- ✅ All commands working (LED, buzzer, sensors)

---

**Status**: ⚠️ **Boards require Arduino IDE compilation to restore functionality**
