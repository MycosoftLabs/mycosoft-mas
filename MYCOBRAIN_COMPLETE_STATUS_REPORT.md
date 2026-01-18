# MycoBrain Complete Status Report
**Date**: January 16, 2026  
**Status**: ⚠️ CRITICAL - Boards Not Operational  
**Issue**: Firmware boot loop on both boards

---

## Executive Summary

After extensive firmware flashing attempts, both MycoBrain ESP32-S3 boards (COM5 and COM7) are experiencing continuous boot loops. All firmware versions tested (Dec 28-30 working versions and newly compiled versions) crash immediately after bootloader entry point.

**Current State:**
- ❌ No LED/NeoPixel activity
- ❌ No buzzer/sound
- ❌ No serial output from firmware
- ✅ Bootloader loads successfully
- ❌ Firmware crashes at entry point `0x403c98d0`

---

## System Architecture (When Working)

### Integration Stack
```
┌─────────────────────────────────────────────────────────────┐
│                    Website (Port 3000)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Device Manager Component                            │   │
│  │  (components/mycobrain-device-manager.tsx)          │   │
│  │  - NeoPixel controls                                 │   │
│  │  - Buzzer presets (coin, bump, power, 1up, morgio)  │   │
│  │  - Sensor telemetry display                         │   │
│  │  - I2C peripheral scanning                          │   │
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
│  │  - Serial port communication (115200 baud)          │   │
│  │  - Command translation (JSON → CLI)                 │   │
│  │  - Telemetry parsing (NDJSON → JSON)                │   │
│  │  - Machine Mode protocol support                    │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │ Serial Communication
                      │ COM5/COM7 (Windows) / /dev/ttyUSB0 (Linux)
                      │ Baud Rate: 115200
                      │ Protocol: Plaintext CLI + NDJSON
┌─────────────────────▼───────────────────────────────────────┐
│         MycoBrain ESP32-S3 (Side-A)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Firmware (CURRENTLY NOT WORKING)                    │   │
│  │  - NeoPixel control (GPIO15, SK6805)                 │   │
│  │  - Buzzer control (GPIO16)                           │   │
│  │  - I2C sensor scanning (GPIO4/5)                     │   │
│  │  - BME688 environmental sensors (0x76, 0x77)         │   │
│  │  - Machine Mode (NDJSON output)                      │   │
│  │  - Plaintext CLI commands                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Hardware Specifications

### ESP32-S3 Configuration
- **MCU**: ESP32-S3 (dual-core Xtensa LX7)
- **Flash**: 16MB QIO @ 80MHz
- **PSRAM**: 8MB OPI ⚠️ **DO NOT ENABLE IN FIRMWARE** (causes brownout/crashes)
- **USB**: Hardware CDC (USB Serial)
- **Crystal**: 40MHz
- **Power**: 5V via USB-C

### Critical Pin Definitions

| GPIO | Function | Type | Notes |
|------|----------|------|-------|
| 4 | I2C SCL | I2C | 100kHz |
| 5 | I2C SDA | I2C | 100kHz |
| 6 | AI1 | Analog Input | ESP32-S3 specific (NOT GPIO34) |
| 7 | AI2 | Analog Input | ESP32-S3 specific (NOT GPIO35) |
| 10 | AI3 | Analog Input | ESP32-S3 specific (NOT GPIO36) |
| 11 | AI4 | Analog Input | ESP32-S3 specific (NOT GPIO39) |
| 12 | MOSFET 1 / LED_R | PWM Output | External MOSFET control |
| 13 | MOSFET 2 / LED_G | PWM Output | External MOSFET control |
| 14 | MOSFET 3 / LED_B | PWM Output | External MOSFET control |
| **15** | **NeoPixel (SK6805)** | **Addressable RGB** | **Requires NeoPixelBus library** |
| **16** | **Buzzer** | **PWM Output** | **Piezo buzzer via MOSFET** |

**⚠️ CRITICAL:** GPIO15 is an **SK6805 NeoPixel** (addressable RGB LED), NOT a simple LED. It requires special timing protocol (WS2812-compatible, 800kHz). Using `digitalWrite()` will not work.

---

## Working Firmware Versions (December 28-30, 2025)

### 1. MycoBrain_SideA_DualMode ✅
- **Date**: December 29, 2025
- **Status**: WAS WORKING (before today's flashing attempts)
- **Features**:
  - Dual mode: CLI and JSON commands
  - Machine Mode (NDJSON output)
  - NeoPixel control (GPIO15)
  - Buzzer sounds (coin, bump, power, 1up, morgio)
  - LED RGB control
  - I2C sensor scanning
  - BME688 support
- **Location**: `firmware/MycoBrain_SideA_DualMode/`
- **Binary**: `build/esp32.esp32.esp32s3/MycoBrain_SideA_DualMode.ino.merged.bin`

### 2. MycoBrain_NeoPixel_Fixed ✅
- **Date**: December 29, 2025
- **Status**: WAS WORKING
- **Features**:
  - Fixed NeoPixel support (SK6812/FastLED)
  - Buzzer sounds
  - LED RGB control
  - BSEC2 sensor support
- **Location**: `firmware/MycoBrain_NeoPixel_Fixed/`
- **Issues Found**: 
  - BSEC2 callback signature mismatch (fixed in code)
  - FastLED LED type (WS2812B → SK6812)
  - SensorSlot initialization issue (fixed in code)

### 3. MycoBrain_Minimal_PIO ✅
- **Date**: January 6, 2026
- **Status**: WAS WORKING on COM7
- **Features**:
  - Minimal firmware
  - Buzzer confirmed working
  - Serial communication
  - NO PSRAM flags
- **Location**: `firmware/MycoBrain_Minimal_PIO/`
- **Binary**: `.pio/build/esp32s3/firmware.bin`

### 4. MycoBrain_ScienceComms ❌
- **Date**: December 30, 2025
- **Status**: NOT WORKING (caused initial failure)
- **Issues**:
  - NeoPixelBus crashes
  - Reset loop issues
  - Incompatible with boards
- **Location**: `firmware/MycoBrain_ScienceComms/`

---

## Current Critical Issue

### Problem: Firmware Boot Loop

**Symptoms:**
```
ESP-ROM:esp32s3-20210327
Build:Mar 27 2021
rst:0x3 (RTC_SW_SYS_RST),boot:0x8 (SPI_FAST_FLASH_BOOT)
Saved PC:0x403cdb0a
SPIWP:0xee
mode:DIO, clock div:1
load:0x3fce3808,len:0x4bc
load:0x403c9700,len:0xbd8
load:0x403cc700,len:0x2a0c
entry 0x403c98d0
[repeats indefinitely]
```

**Analysis:**
- Bootloader loads successfully
- Firmware is loaded from flash
- Firmware crashes immediately at entry point `0x403c98d0`
- No firmware code executes (no Serial, no LED, no buzzer)

**Root Causes Identified:**
1. **PSRAM Configuration**: Firmware compiled with PSRAM flags causes brownout
2. **Bootloader/Partition Mismatch**: Wrong bootloader for the firmware
3. **USB CDC Configuration**: Incompatible USB CDC settings
4. **Compilation Issues**: Pre-compiled binaries may have wrong settings

**Attempted Solutions (All Failed):**
- ✅ Removed PSRAM flags → Still crashes
- ✅ Used NOPSRAM bootloader → Still crashes
- ✅ Flashed complete image (bootloader + partitions + firmware) → Still crashes
- ✅ Tried multiple firmware versions → All crash
- ✅ Compiled fresh with PlatformIO (NO PSRAM) → Still crashes
- ✅ Compiled with Arduino CLI → Still crashes
- ❌ Need Arduino IDE GUI compilation with exact settings

---

## Arduino IDE Settings (From Memory - Known Working)

```
Board: ESP32S3 Dev Module
USB CDC on boot: Enabled ✅
USB DFU on boot: Enabled ✅
USB Firmware MSC on boot: Disabled
USB Mode: Hardware CDC and JTAG ✅
JTAG Adapter: Integrated USB JTAG
PSRAM: OPI PSRAM ⚠️ (May need to be DISABLED)
CPU Frequency: 240 MHz ✅
WiFi Core Debug Level: None
Arduino runs on core: 1
Events run on core: 1
Flash Mode: QIO @ 80 MHz ✅
Flash Size: 16 MB ✅
Partition Scheme: 16MB flash, 3MB app / 9.9MB FATFS ✅
Upload Speed: 921600 ✅
Upload Port: UART0/Hardware CDC
Erase all flash before upload: Disabled
```

---

## Firmware Commands (When Working)

### Plaintext CLI Commands
```
help                          - Show all commands
status                        - Device info and sensor readings
scan                          - I2C bus scan
led rgb <r> <g> <b>          - Set NeoPixel color (0-255)
coin                          - Coin pickup sound
bump                          - Bump sound
power                         - Power-up sound
1up                           - Extra life sound
morgio                        - Morg.io sound
mode machine                  - Enable Machine Mode (NDJSON)
fmt json                      - JSON output format
dbg off                       - Disable debug prints
```

### JSON Commands (Machine Mode)
```json
{"cmd":"status"}
{"cmd":"scan"}
{"cmd":"led","r":255,"g":0,"b":0}
{"cmd":"buzzer","pattern":"coin"}
{"cmd":"buzzer","frequency":1000,"duration":200}
```

---

## Service Architecture

### MycoBrain Service (Port 8003)

**Location**: `services/mycobrain/`

**Key Files:**
- `mycobrain_service_standalone.py` - Main service
- `machine_mode.py` - Machine Mode protocol handler
- `protocol.py` - MDP v1 protocol implementation
- `mas_integration.py` - MAS agent integration

**Features:**
- Device connection management
- Serial port communication (115200 baud)
- Command translation (JSON → CLI)
- Telemetry parsing (NDJSON → JSON)
- Machine Mode support
- Multi-device support

**API Endpoints:**
```
GET  /health                                    - Service health check
GET  /devices                                   - List connected devices
GET  /ports                                     - Scan COM ports
POST /devices/connect/{port}                    - Connect device
POST /devices/disconnect/{device_id}            - Disconnect device
GET  /devices/{device_id}/telemetry            - Get telemetry
POST /devices/{device_id}/command               - Send command
GET  /devices/{device_id}/sensors              - Get sensor data
GET  /devices/{device_id}/peripherals          - I2C peripheral scan
```

---

## Website Integration

### Device Manager Component

**Location**: `components/mycobrain-device-manager.tsx`

**Features:**
- Real-time device status display
- NeoPixel color controls
- Buzzer preset buttons (coin, bump, power, 1up, morgio)
- Custom buzzer frequency/duration
- I2C peripheral scanning
- Sensor telemetry display (BME688)
- Machine Mode initialization

**UI Sections:**
1. **Device Status** - Connection state, MAC address, firmware version
2. **Controls** - NeoPixel and buzzer controls
3. **Sensors** - BME688 temperature, humidity, pressure, gas resistance
4. **Peripherals** - I2C scan results
5. **Telemetry** - Real-time data stream

---

## N8n Workflows

### Workflow 13: MycoBrain Telemetry Forwarder
**Location**: `n8n/workflows/13_mycobrain_telemetry_forwarder.json`

**Purpose**: Forward MycoBrain telemetry to MINDEX and other systems

**Nodes:**
1. Webhook trigger for telemetry
2. Parse NDJSON telemetry
3. Forward to MINDEX
4. Store in PostgreSQL
5. Update Qdrant vector store

### Workflow 14: MycoBrain Optical/Acoustic Modem
**Location**: `n8n/workflows/14_mycobrain_optical_acoustic_modem.json`

**Purpose**: Handle optical and acoustic modem communications

**Features:**
- Optical TX (camera OOK, Manchester encoding)
- Acoustic TX (audio modem)
- Data encoding/decoding
- Error correction

---

## MAS Integration

### Agents

**1. MycoBrain Device Agent**
- Location: `mycosoft_mas/agents/mycobrain/device_agent.py`
- Manages device connections
- Handles command sending with retry logic
- Tracks device state

**2. MycoBrain Ingestion Agent**
- Location: `mycosoft_mas/agents/mycobrain/ingestion_agent.py`
- Ingests telemetry to MINDEX
- Deduplicates using sequence numbers
- Batches data for efficiency

**3. MycoBrain Telemetry Forwarder Agent**
- Location: `mycosoft_mas/agents/mycobrain/telemetry_forwarder_agent.py`
- Forwards telemetry to multiple destinations
- Supports MDP v1 protocol
- Integrates with N8n workflows

---

## Critical Issues and Root Causes

### Issue #1: PSRAM Brownout (RESOLVED → NEW ISSUE)

**Previous Problem**: Firmware with PSRAM flags caused brownout detector to trigger
```
E BOD: Brownout detector was triggered
```

**Solution Applied**: Removed PSRAM flags from platformio.ini
```ini
# REMOVED:
# -DBOARD_HAS_PSRAM
# -mfix-esp32-psram-cache-issue
# board_build.arduino.memory_type = qio_opi
```

**Result**: No more brownout messages, but firmware still crashes

### Issue #2: Firmware Crash at Entry Point (CURRENT)

**Problem**: All firmware versions crash immediately after bootloader loads them

**Evidence**:
```
load:0x3fce3808,len:0x4bc
load:0x403c9700,len:0xbd8
load:0x403cc700,len:0x2a0c
entry 0x403c98d0
[immediate reset, no firmware code executes]
```

**Firmware Versions Tested (All Failed)**:
- MycoBrain_SideA_DualMode (Dec 29 working version)
- MycoBrain_NeoPixel_Fixed (Dec 29 working version)
- MycoBrain_Minimal_PIO (Jan 6 working version)
- MycoBrain_ScienceComms (Dec 30 version)
- MycoBrain_SideA_Simple (NOPSRAM build)
- MycoBrain_MinimalBlink (OTG build)
- Freshly compiled PlatformIO firmware (NO PSRAM)
- Freshly compiled Arduino CLI firmware

**Possible Root Causes**:
1. **Bootloader/Firmware Incompatibility**: Bootloader and firmware compiled with different settings
2. **USB CDC Initialization Failure**: USB CDC crashes before Serial.begin()
3. **Memory Allocation Issue**: Firmware crashes during initialization
4. **Partition Table Mismatch**: Wrong partition scheme for firmware size
5. **Hardware Issue**: Both boards damaged (unlikely)

**What Changed**:
- Before: Firmware was working (LED, buzzer, serial all functional)
- After: Attempted to flash ScienceComms firmware
- Result: All firmware now crashes, even previously working versions

---

## Flashing Procedures Attempted

### Method 1: esptool with Pre-Compiled Binaries
```powershell
python -m esptool --chip esp32s3 --port COM5 --baud 921600 erase_flash
python -m esptool --chip esp32s3 --port COM5 --baud 921600 write_flash \
    0x0 bootloader.bin \
    0x8000 partitions.bin \
    0x10000 firmware.bin
```
**Result**: ❌ Firmware crashes at entry

### Method 2: esptool with Merged Binary
```powershell
python -m esptool --chip esp32s3 --port COM5 --baud 921600 write_flash \
    0x0 MycoBrain_SideA_DualMode.ino.merged.bin
```
**Result**: ❌ Brownout or crash at entry

### Method 3: PlatformIO Compile + Upload
```powershell
cd firmware/MycoBrain_ScienceComms
pio run -t upload --upload-port COM5
```
**Result**: ❌ Firmware crashes at entry

### Method 4: Arduino CLI Compile
```powershell
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,PSRAM=disabled ...
```
**Result**: ❌ Compilation errors or firmware crashes

---

## Solution Required

### Immediate Action Needed

**The boards need firmware compiled with Arduino IDE GUI** using the exact settings from memory. Command-line tools (PlatformIO, arduino-cli, esptool) are creating incompatible binaries.

**Steps:**
1. Open Arduino IDE (1.8.x or 2.x)
2. Open `firmware/MycoBrain_SideA_DualMode/MycoBrain_SideA_DualMode.ino`
3. Configure settings:
   - Board: ESP32S3 Dev Module
   - USB CDC on boot: **Enabled**
   - USB Mode: **Hardware CDC and JTAG**
   - PSRAM: **Disabled** (or OPI PSRAM if board requires)
   - CPU Frequency: 240 MHz
   - Flash Mode: QIO @ 80 MHz
   - Flash Size: 16 MB
   - Partition Scheme: 16MB flash, 3MB app / 9.9MB FATFS
   - Upload Speed: 921600
4. Click **Verify/Compile**
5. Use esptool to flash the generated binaries

**OR**

Find a backup of the working firmware binary from before the ScienceComms upgrade.

---

## Documentation Files

### Core Documentation
1. `MYCOBRAIN_DEVICE_MANAGER_MACHINE_MODE_INTEGRATION.md` - Complete Dec 29 working config (820 lines)
2. `MYCOBRAIN_DEVICE_MANAGER_MACHINE_MODE_EXPLANATION.md` - Machine Mode protocol
3. `MYCOBRAIN_SETUP_COMPLETE.md` - Complete setup history (466 lines)
4. `MYCOBRAIN_STATUS_FINAL.md` - Final status report (225 lines)
5. `MYCOBRAIN_SYSTEM_STATUS_FINAL.md` - System status (228 lines)

### Integration Documentation
6. `docs/integrations/MYCOBRAIN_INTEGRATION.md` - MAS integration guide
7. `MYCOBRAIN_INTEGRATION_SUMMARY.md` - Integration summary
8. `MYCOBRAIN_WEBSITE_INTEGRATION.md` - Website integration

### Testing and Diagnostics
9. `MYCOBRAIN_TEST_RESULTS_COMPLETE.md` - Complete test results (286 lines)
10. `MYCOBRAIN_TESTING_REPORT.md` - Testing report (138 lines)
11. `MYCOBRAIN_CONNECTION_DIAGNOSTICS.md` - Connection diagnostics
12. `MYCOBRAIN_TELEMETRY_ANALYSIS.md` - Telemetry analysis

### Firmware Documentation
13. `scripts/FLASH_MYCOBRAIN_ARDUINO_IDE.md` - Arduino IDE flashing guide
14. `docs/firmware/MYCOBRAIN_PRODUCTION_FIRMWARE.md` - Production firmware docs
15. `MYCOBRAIN_COMMAND_REFERENCE.md` - Command reference

### Quick Start
16. `MYCOBRAIN_QUICKSTART.md` - Quick start guide (182 lines)
17. `FLASH_MYCOBRAIN_NOW.md` - Quick flash instructions

---

## Scripts and Tools

### Testing Scripts
- `scripts/test_mycobrain_all.py` - Comprehensive test suite
- `scripts/test_mycobrain_connection.py` - Connection test
- `scripts/test_mycobrain_commands.py` - Command test
- `scripts/test_mycobrain_serial.py` - Serial communication test
- `scripts/test_both_mycobrain.py` - Test both boards

### Flashing Scripts
- `scripts/flash_mycobrain_production.ps1` - Flash production firmware
- `scripts/flash_mycobrain_sidea.py` - Flash Side-A
- `scripts/flash_mycobrain_direct.py` - Direct flash tool
- `scripts/upload_mycobrain_exact_settings.ps1` - Upload with exact settings

### Diagnostic Scripts
- `scripts/diagnose_mycobrain.py` - Diagnostic tool
- `scripts/diagnose_mycobrain_power.py` - Power diagnostic
- `scripts/mycoboard_autodiscovery.ps1` - Auto-discovery

### Service Scripts
- `scripts/start_mycobrain_service.ps1` - Start service
- `scripts/stop_mycobrain_service.ps1` - Stop service
- `START_MYCOBRAIN_SERVICE.ps1` - Service starter

---

## Next Steps to Restore Functionality

### Immediate (Critical)
1. ✅ Document current failure state (this document)
2. ❌ Compile firmware with Arduino IDE GUI using exact settings
3. ❌ Flash compiled firmware with esptool
4. ❌ Verify LED and buzzer work
5. ❌ Test serial communication
6. ❌ Test Device Manager integration

### Short-Term
1. Start MycoBrain service on port 8003
2. Start website on port 3000
3. Test Device Manager controls
4. Verify telemetry flow
5. Test all commands (coin, bump, led rgb, etc.)

### Long-Term
1. Create automated firmware testing pipeline
2. Backup working firmware binaries
3. Document exact compilation procedure
4. Create recovery procedure
5. Implement firmware version management

---

## Lessons Learned

### Critical Findings
1. **PSRAM MUST be disabled** - Causes brownout and crashes
2. **Arduino IDE compilation required** - Command-line tools create incompatible binaries
3. **Backup working firmware** - Always keep working binaries before upgrades
4. **Test on one board first** - Don't flash both boards simultaneously
5. **Document exact settings** - Settings from memory may not be complete

### What Worked Before
- Arduino IDE compilation with exact settings
- esptool flashing of Arduino IDE binaries
- PlatformIO Minimal firmware (NO PSRAM flags)
- Machine Mode protocol
- Device Manager integration

### What Doesn't Work
- PlatformIO compilation (creates incompatible binaries)
- Arduino CLI compilation (creates incompatible binaries)
- Pre-compiled binaries with PSRAM flags
- ScienceComms firmware (NeoPixelBus crashes)

---

## Recovery Procedure

### Option 1: Arduino IDE Compilation (Recommended)
1. Open Arduino IDE
2. Load `firmware/MycoBrain_SideA_DualMode/MycoBrain_SideA_DualMode.ino`
3. Configure exact settings (see above)
4. Compile (creates bootloader.bin, partitions.bin, firmware.bin)
5. Flash with esptool:
   ```powershell
   python -m esptool --chip esp32s3 --port COM5 --baud 921600 erase_flash
   python -m esptool --chip esp32s3 --port COM5 --baud 921600 write_flash \
       0x0 build/esp32.esp32.esp32s3/MycoBrain_SideA_DualMode.ino.bootloader.bin \
       0x8000 build/esp32.esp32.esp32s3/MycoBrain_SideA_DualMode.ino.partitions.bin \
       0x10000 build/esp32.esp32.esp32s3/MycoBrain_SideA_DualMode.ino.bin
   ```
6. Test for LED and buzzer
7. Repeat for second board

### Option 2: Restore from Backup
1. Find backup of working firmware binary
2. Flash with esptool
3. Test immediately

### Option 3: Hardware Reset
1. Check for hardware damage
2. Verify power supply
3. Check USB cables
4. Test with known-good ESP32-S3 firmware

---

## Current Board Status

### COM5 (Board 1)
- **Detection**: ✅ Detected as ESP32-S3 (VID:PID 303A:1001)
- **Connection**: ✅ Can connect via serial
- **Bootloader**: ✅ Loads successfully
- **Firmware**: ❌ Crashes at entry point
- **LED**: ❌ No activity
- **Buzzer**: ❌ No sound
- **Serial Output**: ❌ Boot loop only

### COM7 (Board 2)
- **Detection**: ✅ Detected as ESP32-S3 (VID:PID 303A:1001)
- **Connection**: ✅ Can connect via serial
- **Bootloader**: ✅ Loads successfully
- **Firmware**: ❌ Crashes at entry point
- **LED**: ❌ No activity
- **Buzzer**: ❌ No sound
- **Serial Output**: ❌ Boot loop only

---

## Recommendations

### Immediate
1. **Stop flashing attempts** - Further flashing may damage boards
2. **Use Arduino IDE** - Only known working compilation method
3. **Test on one board first** - Verify before flashing second board
4. **Document exact procedure** - Record every step for future reference

### Short-Term
1. Create firmware backup system
2. Implement automated testing
3. Document recovery procedures
4. Create firmware version management

### Long-Term
1. Investigate PlatformIO compatibility issues
2. Create standardized build pipeline
3. Implement CI/CD for firmware
4. Create automated testing framework

---

## Contact and Support

**Repository**: https://github.com/MycosoftLabs/mycosoft-mas  
**Firmware**: `firmware/` directory  
**Service**: `services/mycobrain/`  
**Documentation**: `docs/integrations/MYCOBRAIN_INTEGRATION.md`

---

**Status**: ⚠️ **CRITICAL** - Boards require Arduino IDE compilation to restore functionality
