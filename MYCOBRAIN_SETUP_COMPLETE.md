# MycoBrain Board Setup - Complete History & Requirements

**Last Updated**: January 6, 2026  
**Board Status**: ✅ WORKING on COM7 (new board)  
**Firmware**: MycoBrain_Minimal_PIO v1.3.0

## Executive Summary

This document provides the complete history, requirements, and solutions for the MycoBrain ESP32-S3 dual-MCU board. After extensive troubleshooting, the board is now operational with a stable firmware configuration.

## Board Hardware Specifications

### ESP32-S3 Configuration
- **MCU**: ESP32-S3 (dual MCU design)
  - **Side-A**: Sensor MCU (primary, GPIO5/4 I2C, GPIO6/7/10/11 analog)
  - **Side-B**: Router MCU (experimental, UART GPIO16/17)
- **Flash**: 16MB QIO
- **PSRAM**: 8MB OPI (Octal SPI PSRAM) - **DO NOT USE IN FIRMWARE**
- **USB**: Hardware CDC (USB Serial)
- **Power**: 5V via USB-C (Side-B) or Side-A connector
- **Crystal**: 40MHz
- **MAC**: 10:b4:1d:e3:3b:88 (example)

### Critical Pin Definitions

**I2C Bus:**
- SDA: GPIO5
- SCL: GPIO4
- Frequency: 100kHz

**Analog Inputs (CRITICAL - ESP32-S3 specific):**
- AI1: GPIO6 ⚠️ **NOT GPIO34** (classic ESP32)
- AI2: GPIO7 ⚠️ **NOT GPIO35**
- AI3: GPIO10 ⚠️ **NOT GPIO36**
- AI4: GPIO11 ⚠️ **NOT GPIO39**

**RGB LED (PWM):**
- Red: GPIO12
- Green: GPIO13
- Blue: GPIO14

**NeoPixel:**
- GPIO15

**Buzzer:**
- GPIO16

**UART (Side-B Router - EXPERIMENTAL):**
- TX: GPIO16 (conflicts with Side-A buzzer)
- RX: GPIO17

## Critical Setup Issues & Solutions

### Issue #1: Brownout Detector Reset Loop

**Problem**: Board enters continuous reset loop with `E BOD: Brownout detector was triggered`

**Symptoms**:
```
ESP-ROM:esp32s3-20210327
rst:0x3 (RTC_SW_SYS_RST),boot:0x29 (SPI_FAST_FLASH_BOOT)
E BOD: Brownout detector was triggered
[repeats indefinitely]
```

**Root Cause**: 
- Insufficient or unstable USB power delivery
- Brownout detector threshold (2.85V default) too sensitive
- Arduino bootloader has brownout enabled, PlatformIO doesn't

**Solutions**:
1. **Hardware**: 
   - Use high-quality USB-C cable (short, thick, data-rated)
   - Use USB 3.0 port (provides more power)
   - Try powered USB hub
   - Check for short circuits on board

2. **Firmware**: Disable brownout detector in code:
   ```cpp
   #include "soc/rtc_cntl_reg.h"
   WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
   ```

3. **Bootloader**: PlatformIO bootloader is more tolerant than Arduino IDE

**Status**: ✅ **RESOLVED** on new board (intact diode, no bridge modifications)

### Issue #2: PSRAM Configuration Crashes

**Problem**: Firmware crashes or enters reset loop when PSRAM flags are enabled

**Symptoms**:
- Firmware loads but immediately resets
- No brownout errors, just continuous reset loop
- `rst:0x3 (RTC_SW_SYS_RST)` without brownout message

**Root Cause**: 
- Incorrect PSRAM configuration flags
- Mismatch between board hardware and firmware settings
- Memory allocation issues

**Solution**: 
**DO NOT USE PSRAM FLAGS** for stable operation:

```ini
# ❌ DO NOT USE (causes crashes):
build_flags = 
    -DBOARD_HAS_PSRAM
    -mfix-esp32-psram-cache-issue
    -DCONFIG_SPIRAM_MODE_OCT=1
board_build.arduino.memory_type = qio_opi

# ✅ USE THIS (stable):
build_flags = 
    -DARDUINO_USB_MODE=1
    -DARDUINO_USB_CDC_ON_BOOT=1
# No PSRAM flags!
```

**Status**: ✅ **RESOLVED** - Minimal firmware works without PSRAM flags

### Issue #3: Boot Mode Stuck in Download

**Problem**: Board stuck in download mode (`boot:0x1 DOWNLOAD(USB/UART0)`) instead of normal boot

**Symptoms**:
```
ESP-ROM:esp32s3-20210327
rst:0x15 (USB_UART_CHIP_RESET),boot:0x1 (DOWNLOAD(USB/UART0))
waiting for download
```

**Root Cause**: 
- GPIO strapping pins configured for download mode
- Boot button held during reset
- Hardware strapping configuration

**Solutions**:
1. **DO NOT** hold BOOT button during reset
2. Ensure proper hardware strapping (check board schematic)
3. Use `--after hard_reset` flag with esptool
4. Check for hardware modifications (bridges, removed diodes)

**Status**: ⚠️ **BOARD-SPECIFIC** - Some boards may have different strapping configurations

### Issue #4: ArduinoJson Library Crash

**Problem**: Firmware crashes when ArduinoJson library is included

**Root Cause**: 
- Memory allocation issues
- Library incompatibility with ESP32-S3
- PSRAM-related crashes

**Solution**: 
- Use **manual JSON output** (no ArduinoJson library)
- Format JSON strings manually using `Serial.print()` and `Serial.printf()`

**Status**: ✅ **WORKAROUND** - Manual JSON works reliably

### Issue #5: PlatformIO vs Arduino IDE Differences

**Observations**:
- **PlatformIO**: More stable, no brownout issues, different bootloader (ESP-IDF based)
- **Arduino IDE**: Brownout issues on some boards, but was working before with specific settings

**Solution**: 
- Use **PlatformIO** for new firmware development
- Use **Arduino IDE** only if you have a known-working configuration

**Status**: ✅ **RECOMMENDED** - Use PlatformIO for stability

## Working Firmware Configuration

### PlatformIO Configuration (STABLE - CURRENT)

**File**: `firmware/MycoBrain_Minimal_PIO/platformio.ini`

```ini
[env:esp32s3]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
board_build.mcu = esp32s3
board_build.f_cpu = 240000000L
board_build.flash_mode = qio
board_build.flash_size = 16MB
board_build.partitions = default_16MB.csv

# CRITICAL: No PSRAM flags!
build_flags = 
    -DARDUINO_USB_MODE=1
    -DARDUINO_USB_CDC_ON_BOOT=1

upload_speed = 921600
monitor_speed = 115200
```

**Key Features**:
- ✅ No PSRAM configuration (stable)
- ✅ Manual JSON output (no ArduinoJson)
- ✅ Plaintext and JSON command support
- ✅ NeoPixel control (via RGB LED pins)
- ✅ Buzzer control
- ✅ I2C scanning
- ✅ Telemetry every 5 seconds

### Arduino IDE Configuration (If Needed)

**Settings** (from memory - known working before):
- USB CDC on boot: **Enabled**
- USB Mode: **Hardware CDC and JTAG**
- PSRAM: **OPI PSRAM** (but firmware may crash)
- CPU Frequency: **240 MHz**
- Flash Mode: **QIO @ 80 MHz**
- Flash Size: **16 MB**
- Partition Scheme: **16MB Flash, 3MB App / 9.9MB FATFS**
- Upload Speed: **921600**
- Upload Port: **UART0/Hardware CDC**

## Flashing Instructions

### Method 1: Using esptool (Recommended)

```powershell
# Flash PlatformIO firmware
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

$basePath = "firmware\MycoBrain_Minimal_PIO\.pio\build\esp32s3"

python -m esptool --chip esp32s3 --port COM7 --baud 921600 write_flash `
    0x0 "$basePath\bootloader.bin" `
    0x8000 "$basePath\partitions.bin" `
    0x10000 "$basePath\firmware.bin"
```

### Method 2: Using PlatformIO

```powershell
cd firmware\MycoBrain_Minimal_PIO
python -m platformio run --target upload --upload-port COM7
```

### Method 3: Using Arduino IDE

1. Open `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`
2. Select board: **ESP32S3 Dev Module**
3. Configure settings as above
4. Upload

## Command Protocol

### Plaintext Commands (CLI Mode)

```
status          - Get device status (JSON)
scan            - Scan I2C bus and return status
led red         - Set LED to red (255,0,0)
led green       - Set LED to green (0,255,0)
led blue        - Set LED to blue (0,0,255)
led off         - Turn LED off (0,0,0)
buzzer beep     - Play beep sound (1000Hz, 100ms)
buzzer coin     - Play coin sound (988Hz->1319Hz)
mode machine    - Enable machine mode (NDJSON output)
mode human      - Disable machine mode
fmt json        - JSON output format
fmt lines       - Plaintext output format
```

### JSON Commands (Website/Service)

The website sends commands via the service API:

**Format 1** (Service sends directly):
```json
{"command_type":"set_neopixel","r":255,"g":0,"b":0}
```

**Format 2** (Nested):
```json
{"command":{"command_type":"set_neopixel","r":255,"g":0,"b":0}}
```

**Format 3** (Website component):
```json
{"command":"set_neopixel","parameters":{"r":255,"g":0,"b":0}}
```

**Supported Commands**:
- `set_neopixel` - Control RGB LED/NeoPixel
  - Parameters: `r`, `g`, `b` (0-255) or `all_off: true`
- `set_buzzer` - Control buzzer
  - Parameters: `frequency` (Hz), `duration` (ms) or `off: true`
- `i2c_scan` - Scan I2C bus
- `status` - Get device status

## Device Manager Integration

### Service Architecture

```
Website (port 3000)
  ↓
API Route (/api/mycobrain/command)
  ↓
MycoBrain Service (port 8003)
  ↓
Serial Port (COM7, 115200 baud)
  ↓
MycoBrain Firmware
```

### Service Endpoints

- **Health**: `GET http://localhost:8003/health`
- **Devices**: `GET http://localhost:8003/devices`
- **Ports**: `GET http://localhost:8003/ports`
- **Connect**: `POST http://localhost:8003/devices/connect/{port}`
- **Command**: `POST http://localhost:8003/devices/{device_id}/command`
- **Telemetry**: `GET http://localhost:8003/devices/{device_id}/telemetry`
- **Disconnect**: `POST http://localhost:8003/devices/{device_id}/disconnect`

### Website Integration

- **Device Manager**: `http://localhost:3000/natureos/devices`
- **API Route**: `POST /api/mycobrain/command`

The website component (`components/mycobrain-device-manager.tsx`) sends commands via the API route, which forwards to the service.

## Testing Checklist

### Basic Functionality
- [x] Board powers on (green NeoPixel on Side-A)
- [x] Serial output visible at 115200 baud
- [x] No brownout errors
- [x] No reset loops
- [x] `status` command responds
- [x] `led red/green/blue/off` commands work
- [x] `buzzer beep/coin` commands work
- [x] `scan` command detects I2C devices
- [x] Telemetry sent every 5 seconds

### Website Integration
- [x] Website Device Manager shows device connected
- [ ] Website NeoPixel controls work (needs firmware update)
- [ ] Website Buzzer controls work (needs firmware update)
- [ ] Machine mode initialization works (needs firmware update)

## Known Working Firmware Versions

### 1. MycoBrain_Minimal_PIO (Current - WORKING)
- **Build**: PlatformIO
- **Config**: No PSRAM flags
- **Features**: Manual JSON, plaintext + JSON commands
- **Status**: ✅ **WORKING** - All basic features
- **Location**: `firmware/MycoBrain_Minimal_PIO/`

### 2. MycoBrain_SideA_DualMode (Previous - PARTIAL)
- **Build**: Arduino IDE
- **Config**: OPI PSRAM enabled
- **Features**: ArduinoJson, DualMode (CLI + JSON)
- **Status**: ⚠️ **PARTIAL** - Was working before but has brownout issues
- **Location**: `firmware/MycoBrain_SideA_DualMode/`

### 3. MycoBrain_ScienceComms (Experimental - NOT WORKING)
- **Build**: PlatformIO
- **Config**: OPI PSRAM, NeoPixelBus library
- **Features**: Advanced science features, NeoPixelBus
- **Status**: ❌ **NOT WORKING** - Reset loop issues (NeoPixelBus crash)
- **Location**: `firmware/MycoBrain_ScienceComms/`

## Troubleshooting Guide

### Board Not Responding

1. **Check COM port**:
   ```powershell
   python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"
   ```

2. **Check power**: Green NeoPixel should be on (Side-A)

3. **Try different USB cable/port**: Use USB 3.0 port, high-quality cable

4. **Check for brownout errors**: Look for `E BOD` in serial output

5. **Try resetting board**: Unplug/replug USB

### Firmware Crashes

1. **Remove PSRAM flags** from `platformio.ini`
2. **Remove ArduinoJson library** (use manual JSON)
3. **Disable brownout detector** in code
4. **Use minimal firmware first**, then add features incrementally

### Website Not Controlling Board

1. **Check MycoBrain service**:
   ```powershell
   curl http://localhost:8003/health
   ```

2. **Check device connection**:
   ```powershell
   curl http://localhost:8003/devices
   ```

3. **Check command format**: Service sends `{"command_type":"..."}` format

4. **Check serial port**: Ensure not locked by another application

5. **Check firmware**: Must support JSON command parsing

## Next Steps for Full Website Integration

1. **Update firmware** to handle service command format:
   - Parse `{"command_type":"set_neopixel","r":255,"g":0,"b":0}`
   - Parse `{"command_type":"set_buzzer","frequency":1000,"duration":200}`
   - Return proper JSON responses

2. **Add machine mode initialization**:
   - Support `mode machine` command
   - Enable NDJSON output format
   - Support all machine mode features

3. **Test all website controls**:
   - NeoPixel color picker
   - Buzzer frequency/duration controls
   - MOSFET controls
   - I2C scan button

4. **Create comprehensive test suite**:
   - Automated testing script
   - Website integration tests
   - Service API tests

## Summary

**Critical Requirements for Stable Operation**:
1. ✅ **NO PSRAM flags** in PlatformIO config
2. ✅ **Manual JSON output** (no ArduinoJson library)
3. ✅ **PlatformIO build** (more stable than Arduino IDE)
4. ✅ **Proper power supply** (2A+ USB-C, USB 3.0 port)
5. ✅ **Correct pin definitions** (ESP32-S3 specific, not classic ESP32)

**Current Status**: 
- ✅ Board working on COM7 with minimal firmware
- ✅ Basic commands working (LED, buzzer, I2C scan)
- ✅ Telemetry flowing
- ⚠️ Website integration needs firmware update for JSON command format
- ⚠️ Full DualMode features need to be ported to stable PlatformIO config

**Recommended Action**:
1. Update `firmware/MycoBrain_Minimal_PIO/src/main.cpp` to handle service JSON command format
2. Test via website Device Manager
3. Add machine mode support
4. Test all website controls

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-06  
**Board Revision**: New board (intact diode, no bridge)  
**Firmware Version**: 1.3.0 (dualmode-complete)  
**Status**: ✅ **WORKING** (basic features), ⚠️ **IN PROGRESS** (website integration)
