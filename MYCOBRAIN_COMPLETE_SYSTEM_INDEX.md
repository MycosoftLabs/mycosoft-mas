# MycoBrain Complete System Index
**Date**: January 6, 2026  
**Purpose**: Complete understanding of MycoBrain system, all working configurations, and restoration procedures

## Executive Summary

After comprehensive documentation review, the working configuration from **December 28-30, 2024** used:
- **Arduino IDE** to compile firmware (creates bootloader.bin, partitions.bin, firmware.bin)
- **esptool** to flash the compiled binaries
- **DualMode firmware** that supports both CLI and JSON commands
- **Machine Mode** for NDJSON output to Device Manager

## Working Firmware Versions (Dec 28-30)

1. **MycoBrain_SideA_Production** - Production firmware
2. **MycoBrain_SideA_DualMode** - Dual mode (CLI + JSON) ✅ **THIS WAS WORKING**
3. **MycoBrain_SideA_Fixed** - Fixed version
4. **MycoBrain_SideA_NeoPixel_Fixed** - NeoPixel fixed version

**All were compiled with Arduino IDE and flashed with esptool.**

## Complete Arduino IDE Settings (Dec 29 Working)

```
Board: ESP32S3 Dev Module
USB CDC on boot: Enabled ✅
USB DFU on boot: Enabled ✅
USB Firmware MSC on boot: Disabled
USB Mode: Hardware CDC and JTAG ✅
JTAG Adapter: Integrated USB JTAG
PSRAM: OPI PSRAM
CPU Frequency: 240 MHz
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

## Hardware Configuration

### Pins (Critical)
- **NeoPixel (SK6805)**: GPIO15 (addressable RGB, NOT PWM)
- **Buzzer**: GPIO16
- **I2C SDA**: GPIO5
- **I2C SCL**: GPIO4
- **Analog Inputs**: GPIO6, GPIO7, GPIO10, GPIO11 (ESP32-S3 specific)

### Commands (Working Dec 29)
**Plaintext CLI:**
- `led rgb <r> <g> <b>` - NeoPixel control
- `coin`, `bump`, `power`, `1up`, `morgio` - Buzzer sounds
- `status`, `scan`, `help` - Device info
- `mode machine` - Enable NDJSON
- `fmt json` - JSON output

## Flashing Procedure (CORRECT)

### Step 1: Compile with Arduino IDE (One-Time)
1. Open `.ino` file in Arduino IDE
2. Select board: **ESP32S3 Dev Module**
3. Configure all settings (see above)
4. Click **Verify/Compile** (creates build folder with binaries)

### Step 2: Flash with esptool
**Arduino IDE creates:**
- `build/esp32.esp32.esp32s3/bootloader.bin` (flash at 0x0)
- `build/esp32.esp32.esp32s3/partitions.bin` (flash at 0x8000)
- `build/esp32.esp32.esp32s3/MycoBrain_SideA_DualMode.ino.bin` (flash at 0x10000)

**esptool command:**
```powershell
python -m esptool --chip esp32s3 --port COM4 --baud 921600 write-flash \
    0x0 bootloader.bin \
    0x8000 partitions.bin \
    0x10000 MycoBrain_SideA_DualMode.ino.bin
```

## Current Issue

**Problem**: Bootloader and partitions.bin are missing from build folder
**Root Cause**: Arduino IDE hasn't been used to compile the firmware yet
**Solution**: 
1. Compile with Arduino IDE first (creates all 3 files)
2. Then use esptool to flash all 3 files

## System Architecture (Working Dec 29)

```
Website (localhost:3000)
  ↓ HTTP REST API
MycoBrain Service (localhost:8003)
  ↓ Serial (115200 baud, plaintext CLI)
MycoBrain ESP32-S3 Side-A
  - Firmware: v3.3.5 DualMode
  - NeoPixel: GPIO15
  - Buzzer: GPIO16
  - Commands: coin, bump, led rgb, status
  - Machine Mode: NDJSON output
```

## Documentation Files Index

### Core Working Configuration
1. `MYCOBRAIN_DEVICE_MANAGER_MACHINE_MODE_INTEGRATION.md` - **MOST IMPORTANT** - Complete Dec 29 working config
2. `MYCOBRAIN_DEVICE_MANAGER_MACHINE_MODE_EXPLANATION.md` - Machine Mode protocol
3. `scripts\FLASH_MYCOBRAIN_ARDUINO_IDE.md` - Arduino IDE flashing guide

### Setup and Status
4. `MYCOBRAIN_SETUP_COMPLETE.md` - Complete setup history
5. `DUAL_MODE_FIRMWARE_STATUS.md` - DualMode status
6. `SYSTEM_AUDIT_AND_FIXES.md` - System issues

### Integration
7. `docs/integrations/MYCOBRAIN_INTEGRATION.md` - MAS integration
8. `MYCOBRAIN_INTEGRATION_SUMMARY.md` - Integration summary

## Key Learnings

1. **Arduino IDE compiles, esptool flashes** - Two-step process
2. **All three binaries required** - bootloader, partitions, firmware
3. **Partition scheme critical** - 3MB app / 9.9MB FATFS
4. **USB CDC on boot must be Enabled** - Required for serial
5. **DualMode firmware supports both CLI and JSON** - This is what worked

## Next Steps

1. **Compile DualMode firmware with Arduino IDE** (creates all 3 binaries)
2. **Flash all 3 binaries with esptool** (bootloader + partitions + firmware)
3. **Test physically** (LED and beep)
4. **Test serial** (115200 baud)
5. **Test Device Manager** (website buttons)

---

**Status**: System fully indexed and understood. Ready to restore working configuration.
