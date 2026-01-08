# MycoBrain System State Snapshot
**Timestamp**: January 8, 2026, 12:30 PM PST  
**Purpose**: Pre-ScienceComms Integration Checkpoint  
**Author**: Claude AI + Human Review  

---

## Executive Summary

This document captures the EXACT state of the MycoBrain Device Manager system BEFORE implementing ScienceComms features (optical/acoustic modem). This serves as a rollback checkpoint.

---

## System Components

### 1. Hardware
- **Board**: ESP32-S3 Dev Module (MycoBrain v1.0)
- **Port**: COM7
- **NeoPixel**: SK6805 on GPIO15 (1 LED)
- **Buzzer**: Passive on GPIO16 (LEDC PWM)
- **Peripherals Connected**: NONE (bare board test)

### 2. Firmware
- **File**: `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`
- **Version**: 1.1.0 (custom build)
- **Libraries**: Adafruit_NeoPixel, ArduinoJson

### 3. Python Service
- **File**: `minimal_mycobrain.py`
- **Port**: 8003
- **Framework**: FastAPI

### 4. Website
- **Path**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
- **Port**: 3002
- **URL**: http://localhost:3002/natureos/devices?device=COM7

---

## ✅ WORKING Features (Verified)

### Firmware Commands (Terminal Tested)

| Command | Function | Status |
|---------|----------|--------|
| `status` | Get device status | ✅ Working |
| `led rgb R G B` | Set LED color (0-255) | ✅ Working |
| `led mode off` | Turn LED off | ✅ Working |
| `led mode state` | Green pulse indicator | ✅ Working |
| `led mode manual` | Manual RGB control | ✅ Working |
| `led brightness 0-100` | Set brightness percentage | ✅ Working |
| `led pattern solid` | Solid color | ✅ Working |
| `led pattern blink` | Blinking pattern | ✅ Working |
| `led pattern breathe` | Breathing fade | ✅ Working |
| `led pattern rainbow` | Rainbow cycle | ✅ Working |
| `led pattern chase` | Chase pattern | ✅ Working |
| `led pattern sparkle` | Random sparkle | ✅ Working |
| `beep [freq] [ms]` | Play buzzer tone | ✅ Working |
| `coin` | Coin pickup sound | ✅ Working |
| `bump` | Bump sound | ✅ Working |
| `power` | Power-up sound | ✅ Working |
| `1up` | Extra life sound | ✅ Working |
| `morgio` | SuperMorgio jingle | ✅ Working |
| `scan` / `i2c_scan` | Scan I2C bus | ✅ Working |
| `help` | Show commands | ✅ Working |

### Website UI Controls (Browser Tested)

| Control | Widget | API Route | Status |
|---------|--------|-----------|--------|
| Beep button | Buzzer Control | `/api/mycobrain/{port}/buzzer` | ✅ Working |
| Melody button | Buzzer Control | `/api/mycobrain/{port}/buzzer` | ✅ Working (morgio) |
| Set Color button | LED Control Widget | `/api/mycobrain/{port}/led` | ✅ Working |
| Rainbow button | LED Control Widget | `/api/mycobrain/{port}/led` | ✅ Working |
| Color presets (Red/Green/Blue) | Legacy NeoPixel | `/api/mycobrain/{port}/control` | ✅ Working |
| Pattern buttons (solid/blink/etc) | LED Control Widget | `/api/mycobrain/{port}/led` | ✅ Working |

---

## ❌ NOT WORKING Features

### UI Issues (Identified but NOT yet fixed)

| Issue | Widget Location | Current Behavior | Root Cause |
|-------|-----------------|------------------|------------|
| **Legacy Brightness Slider** | NeoPixel Legacy section | No visible LED change | API sends brightness, but with RGB (applies to next color) |
| **LED Control Brightness** | LED Control Widget | Sends command on slide | Sends `led brightness {value}` - works, but no immediate visible feedback if color is black |
| **Optical TX** | Comms tab | Shows "Idle" | Feature NOT implemented in firmware |
| **Acoustic TX** | Comms tab | Shows "Idle" | Feature NOT implemented in firmware |
| **Sensor Banner** | Top header | Shows "2x BME688" | Hardcoded, not reading from firmware |
| **Machine Mode** | Controls tab | Shows "Not Initialized" | Feature partially implemented |

### Features Missing from Firmware

| Feature | ScienceComms Has | Current Firmware Has |
|---------|------------------|----------------------|
| `optx start/stop/status` | ✅ Yes | ❌ No |
| `aotx start/stop/status` | ✅ Yes | ❌ No |
| `stim light/sound` | ✅ Yes | ❌ No |
| `periph hotplug` | ✅ Yes | ❌ No |
| `out set/pwm` | ✅ Yes | ⚠️ Placeholder |

---

## Widget Conflicts Analysis

### Two LED Control Widgets Present

The Controls tab has TWO LED control sections that may conflict:

1. **"NeoPixel LED Control (Legacy)"** - Uses `/api/mycobrain/{port}/control` route
   - RGB sliders (0-255)
   - Brightness slider (0-255, converted to 0-100%)
   - Set Color button
   - Rainbow button
   - Color presets (Red, Green, Blue, Yellow, Cyan, Magenta, White, Warm)

2. **"LED Control" Widget** (separate component) - Uses `/api/mycobrain/{port}/led` route
   - RGB sliders (0-255)
   - Brightness slider (0-100)
   - Apply Color button
   - Pattern buttons (solid, blink, breathe, rainbow, chase, sparkle)
   - Optical TX tab

### Brightness Behavior

**Legacy Widget** (control route):
- Slider value: 0-255
- Sends: `led brightness ${brightnessPercent}` (converted to 0-100)
- Then sends: `led rgb ${r} ${g} ${b}`
- Issue: Brightness is applied BEFORE RGB, so changing brightness alone with R=G=B=0 shows nothing

**LED Control Widget** (led route):
- Slider value: 0-100
- Sends: `led brightness ${value}` on every slider move
- Works correctly, but sends too many commands

---

## API Route Mapping

| Widget Action | API Route | CLI Command Sent |
|---------------|-----------|------------------|
| Legacy Set Color | `/control` (neopixel) | `led rgb R G B` |
| Legacy Rainbow | `/control` (neopixel) | `led pattern rainbow` |
| Legacy Off | `/control` (neopixel) | `led mode off` |
| LED Widget RGB | `/led` (rgb) | `led rgb R G B` |
| LED Widget Pattern | `/led` (pattern) | `led pattern {name}` |
| LED Widget Brightness | `/led` (brightness) | `led brightness {value}` |
| LED Widget Optical | `/led` (optical_tx) | JSON: `optical.tx.start` |
| Buzzer Beep | `/buzzer` (beep) | `beep 1000 200` |
| Buzzer Melody | `/buzzer` (melody) | `morgio` |
| Buzzer Preset | `/buzzer` (preset) | `coin` / `bump` / etc |

---

## File Locations Reference

### Firmware
- **Current**: `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`
- **ScienceComms Source**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms\src\`

### Python Service
- **Main**: `minimal_mycobrain.py` (root of mycosoft-mas)

### Website (Separate Repo)
- **LED API**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\api\mycobrain\[port]\led\route.ts`
- **Buzzer API**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\api\mycobrain\[port]\buzzer\route.ts`
- **Control API**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\api\mycobrain\[port]\control\route.ts`
- **Device Manager**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\components\mycobrain\mycobrain-device-manager.tsx`
- **LED Widget**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\components\mycobrain\widgets\led-control-widget.tsx`
- **Buzzer Widget**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\components\mycobrain\widgets\buzzer-control-widget.tsx`

---

## Arduino IDE Settings (Verified Working)

```
Board: ESP32-S3 Dev Module
USB CDC on Boot: Enabled
USB DFU on Boot: Enabled
USB Mode: Hardware CDC and JTAG
JTAG Adapter: Integrated USB JTAG
PSRAM: OPI PSRAM
CPU Frequency: 240 MHz
Flash Mode: QIO 80MHz
Flash Size: 16MB (128Mb)
Partition Scheme: 16M Flash (3MB APP / 9.9MB FATFS)
Upload Speed: 921600
```

**Arduino CLI FQBN**:
```
esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=cdc,DFUOnBoot=dfu,FlashMode=qio,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,DebugLevel=none
```

---

## Known Bug Fixes Applied

### 1. NeoPixel Library Change
- **Problem**: FastLED with WS2812B config didn't work for SK6805
- **Solution**: Switched to Adafruit_NeoPixel with `NEO_GRB + NEO_KHZ800`

### 2. Buzzer tone() Not Working
- **Problem**: `tone()` function not supported on ESP32-S3
- **Solution**: Use LEDC: `ledcWriteTone()`, `ledcSetup()`, `ledcAttachPin()`

### 3. Browser Resource Exhaustion
- **Problem**: Too many concurrent requests from aggressive polling
- **Solution**: Reduced polling intervals, added mutex

### 4. Website "Failed to fetch"
- **Problem**: Nested command format not parsed
- **Solution**: Updated minimal_mycobrain.py to handle `{command:{cmd:...}}`

---

## ScienceComms Features to Port

From `C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms\src\`:

1. **modem_optical.cpp** - Optical TX (OOK, Manchester, patterns)
2. **modem_audio.cpp** - Acoustic TX (FSK, sweep, chirp)
3. **stimulus.cpp** - Light/sound experiment patterns
4. **peripherals.cpp** - I2C hotplug detection

### Why ScienceComms Broke Last Time:
1. `main.cpp` was a test stub, not the real firmware
2. Used NeoPixelBus instead of Adafruit_NeoPixel
3. PSRAM was disabled in platformio.ini
4. Used `tone()` instead of LEDC for buzzer

---

## Next Steps (Planned)

### Phase 1: Fix UI Issues (No Firmware Changes)
1. Remove duplicate LED control widgets OR unify behavior
2. Fix brightness slider to apply visible change
3. Update sensor banner to show "No Sensors" when none detected

### Phase 2: Port Optical TX (Firmware + API)
1. Add `optx` command handlers to DeviceManager firmware
2. Test via terminal
3. Verify UI shows "Running" during transmission

### Phase 3: Port Acoustic TX (Firmware + API)
1. Add `aotx` command handlers to DeviceManager firmware
2. Test via terminal
3. Verify UI shows "Running" during transmission

---

## Rollback Procedure

If changes break the board:

1. Stop services: `Stop-Process -Name python -Force`
2. Enter bootloader: Hold BOOT, press RESET, release BOOT
3. Flash known-good firmware (this checkpoint)
4. Restart services

---

**Document Version**: 1.0  
**Checkpoint Created**: 2026-01-08 12:30 PM PST  
**Git Commit**: (to be added after push)
