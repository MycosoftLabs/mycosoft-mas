# MycoBrain System State Documentation
**Timestamp**: January 8, 2026, 12:45 PM PST  
**Board**: ESP32-S3 on COM7  
**Firmware**: MycoBrain_DeviceManager v1.1.0  
**Service**: minimal_mycobrain.py v2.2.0  
**Website**: Port 3002

---

## Executive Summary

This document captures the complete state of the MycoBrain Device Manager system BEFORE implementing ScienceComms features. All basic LED and buzzer controls are working. Optical and Acoustic TX features are NOT yet implemented.

---

## ✅ WORKING Features

### 1. Hardware Controls (Firmware → Physical Hardware)

| Feature | Command | Status | Notes |
|---------|---------|--------|-------|
| **NeoPixel LED (GPIO15)** | `led rgb R G B` | ✅ Working | Adafruit_NeoPixel library |
| **LED Mode Off** | `led mode off` | ✅ Working | |
| **LED Mode State** | `led mode state` | ✅ Working | Green pulse animation |
| **LED Mode Manual** | `led mode manual` | ✅ Working | |
| **LED Brightness** | `led brightness 0-100` | ✅ Working | Scales RGB values |
| **LED Pattern Solid** | `led pattern solid` | ✅ Working | |
| **LED Pattern Blink** | `led pattern blink` | ✅ Working | |
| **LED Pattern Breathe** | `led pattern breathe` | ✅ Working | |
| **LED Pattern Rainbow** | `led pattern rainbow` | ✅ Working | |
| **LED Pattern Chase** | `led pattern chase` | ✅ Working | |
| **LED Pattern Sparkle** | `led pattern sparkle` | ✅ Working | |
| **Buzzer Beep** | `beep [freq] [ms]` | ✅ Working | LEDC PWM (not tone()) |
| **Sound: Coin** | `coin` | ✅ Working | Mario coin pickup |
| **Sound: Bump** | `bump` | ✅ Working | |
| **Sound: Power** | `power` | ✅ Working | |
| **Sound: 1UP** | `1up` | ✅ Working | |
| **Sound: Morgio** | `morgio` / `melody` | ✅ Working | Custom jingle |
| **I2C Scan** | `scan` / `i2c_scan` | ✅ Working | |
| **Status** | `status` | ✅ Working | |
| **Telemetry** | Auto every 2s | ✅ Working | JSON format |

### 2. Service API (minimal_mycobrain.py)

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | ✅ Working | |
| `/devices` | GET | ✅ Working | |
| `/ports` | GET | ✅ Working | Cached, timeout-protected |
| `/devices/connect/{port}` | POST | ✅ Working | |
| `/devices/disconnect/{port}` | POST | ✅ Working | |
| `/devices/{device_id}/telemetry` | GET | ✅ Working | CLI "status" command |
| `/devices/{device_id}/command` | POST | ✅ Working | Supports nested `{command:{cmd:...}}` |
| `/devices/{device_id}/cli` | POST | ✅ Working | Raw CLI commands |

### 3. Website UI Controls (Tested Working)

| Control | UI Location | API Route | Status |
|---------|-------------|-----------|--------|
| **Beep Button** | Controls tab | `/api/mycobrain/{port}/buzzer` | ✅ Working |
| **Melody Button** | Controls tab | `/api/mycobrain/{port}/buzzer` | ✅ Working (morgio) |
| **Set Color Button** | Controls tab | `/api/mycobrain/{port}/led` | ✅ Working |
| **Rainbow Button** | Controls tab | `/api/mycobrain/{port}/led` | ✅ Working |
| **Color Presets (Red, Green, etc.)** | Controls tab | `/api/mycobrain/{port}/control` | ✅ Working |

---

## ❌ NOT WORKING Features

### 1. UI Issues Identified

| Issue | Location | Current Behavior | Expected Behavior |
|-------|----------|------------------|-------------------|
| **Brightness Slider (Legacy LED)** | NeoPixel Legacy section | No visible effect | Should dim LED |
| **Brightness Slider (LED Control Widget)** | LED Control Widget | Sends command, may not update LED | Should dim LED visually |
| **Custom Tone Slider** | Buzzer Control | May not send correct command | Should play custom frequency |
| **Optical TX** | Comms tab | Shows "Idle" | Feature not implemented in firmware |
| **Acoustic TX** | Comms tab | Shows "Idle" | Feature not implemented in firmware |
| **Machine Mode Initialize** | Controls tab | Says "Not Initialized" | Feature partially implemented |
| **Sensor Banner** | Top of page | Shows "2x BME688" | Should show "No Sensors" when none connected |

### 2. Features NOT in Current Firmware

| Feature | ScienceComms Has | Current Firmware Has |
|---------|------------------|----------------------|
| **Optical Modem TX** | ✅ optx start/stop/status | ❌ Not implemented |
| **Acoustic Modem TX** | ✅ aotx start/stop/status | ❌ Not implemented |
| **Stimulus Engine** | ✅ stim light/sound | ❌ Not implemented |
| **Peripheral Hotplug** | ✅ periph hotplug | ❌ Not implemented |
| **Digital Outputs (MOSFET)** | ✅ out set/pwm | ⚠️ Placeholder only |
| **Machine Mode NDJSON** | ✅ mode machine | ⚠️ fmt json (similar) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Website (Port 3002)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Device Manager UI (/natureos/devices?device=COM7)        │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │  │
│  │  │ LED Control  │ │ Buzzer Ctrl  │ │ Comms (TODO) │       │  │
│  │  │ - RGB sliders│ │ - Beep       │ │ - Optical TX │       │  │
│  │  │ - Brightness │ │ - Melody     │ │ - Acoustic TX│       │  │
│  │  │ - Patterns   │ │ - Custom tone│ │ - (Idle)     │       │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│           Next.js API Routes (/api/mycobrain/[port]/...)        │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│              MycoBrain Service (Port 8003)                       │
│              minimal_mycobrain.py v2.2.0                         │
│              - FastAPI                                           │
│              - Serial port handling                              │
│              - CLI + JSON command routing                        │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│              ESP32-S3 Firmware on COM7                           │
│              MycoBrain_DeviceManager.ino v1.1.0                  │
│              - Adafruit_NeoPixel (GPIO15)                        │
│              - LEDC Buzzer (GPIO16)                              │
│              - ArduinoJson                                       │
│              - CLI + JSON dual mode                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Firmware Technical Details

### Pin Configuration (Verified Working)

```cpp
// I2C
SDA: GPIO5
SCL: GPIO4
Frequency: 100kHz

// NeoPixel (SK6805)
NEOPIXEL_PIN: GPIO15
PIXEL_COUNT: 1
Library: Adafruit_NeoPixel with NEO_GRB + NEO_KHZ800

// Buzzer (LEDC PWM)
BUZZER_PIN: GPIO16
BUZZER_LEDC_CHANNEL: 0
BUZZER_LEDC_RESOLUTION: 8

// MOSFET Outputs (not currently used for LED)
AO_PINS: {12, 13, 14}
```

### Arduino IDE Settings (For Flashing)

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
Partition Scheme: 16M Flash (3MB APP / 9.9MB FATFS) - app3M_fat9M_16MB
Upload Speed: 921600
```

### Libraries Required

```
arduino-cli lib install "Adafruit NeoPixel"
arduino-cli lib install "ArduinoJson"
```

---

## Known Issues & Bug Fixes Applied

### 1. NeoPixel Not Working (Fixed)
- **Problem**: FastLED with WS2812B config didn't work for SK6805
- **Solution**: Switched to Adafruit_NeoPixel with NEO_GRB + NEO_KHZ800

### 2. Buzzer Not Working (Fixed)
- **Problem**: `tone()` function not supported on ESP32-S3
- **Solution**: Use LEDC peripheral with `ledcWriteTone()`, `ledcSetup()`, `ledcAttachPin()`

### 3. Browser ERR_INSUFFICIENT_RESOURCES (Fixed)
- **Problem**: Too many concurrent network requests from aggressive polling
- **Solution**: 
  - Reduced autoScanAndConnect interval from 3s to 10s
  - Added mutex to prevent concurrent runs
  - Increased telemetry poll interval from 2s to 15s
  - Removed automatic sensor polling for all devices

### 4. Website "Failed to fetch" (Fixed)
- **Problem**: Nested command format `{command:{cmd:...}}` not parsed correctly
- **Solution**: Updated minimal_mycobrain.py to extract nested `cmd` field

### 5. Brownout Reset Loop (Documented)
- **Problem**: Board enters reset loop with brownout errors
- **Solution**: 
  - Disable brownout in firmware: `WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0)`
  - Use good quality USB cable and USB 3.0 port

---

## ScienceComms Firmware Analysis

The ScienceComms firmware in `C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms` contains these additional features:

### Why ScienceComms Broke:

1. **main.cpp is a minimal test** - Not the real firmware, just a debugging stub
2. **Uses NeoPixelBus** - Incompatible with SK6805 (needs Adafruit_NeoPixel)
3. **PSRAM disabled** - `board_build.arduino.memory_type = qio_opi` commented out
4. **Uses tone()** - Doesn't work on ESP32-S3

### Features to Port:

1. **Optical Modem** (modem_optical.cpp)
   - OOK (On-Off Keying) transmission
   - Manchester encoding
   - Pattern modes (pulse, beacon, sweep)
   - CRC16 checksum

2. **Acoustic Modem** (modem_audio.cpp)
   - FSK (Frequency Shift Keying)
   - Sweep and chirp patterns
   - Payload encoding

3. **Stimulus Engine** (stimulus.cpp)
   - Light patterns with cycles
   - Sound patterns with frequency sweeps
   - Combined light+sound experiments

4. **Peripheral Discovery** (peripherals.cpp)
   - I2C device identification
   - Hotplug detection
   - Device registry

---

## Next Steps (Hybrid Firmware Plan)

### Phase 1: Fix UI Issues
1. Fix brightness slider not updating LED
2. Fix custom tone slider
3. Update sensor banner to show "No Sensors"

### Phase 2: Port Optical TX
1. Add optx command handlers to firmware
2. Add optical pattern state machine
3. Test with camera/photodiode

### Phase 3: Port Acoustic TX
1. Add aotx command handlers to firmware
2. Add FSK transmission state machine
3. Test with microphone

### Phase 4: Port Stimulus Engine
1. Add stim command handlers
2. Add light/sound pattern scheduling
3. Test experiment workflows

---

## File Locations

| Component | Path |
|-----------|------|
| **Current Firmware** | `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino` |
| **ScienceComms Source** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms\src\` |
| **Python Service** | `minimal_mycobrain.py` |
| **Website LED API** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\api\mycobrain\[port]\led\route.ts` |
| **Website Buzzer API** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\api\mycobrain\[port]\buzzer\route.ts` |
| **Device Manager UI** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\components\mycobrain\mycobrain-device-manager.tsx` |

---

## Git Status Before Changes

This document serves as a checkpoint. Before implementing ScienceComms features:

1. ✅ Document current state (this file)
2. ⏳ Commit all current changes
3. ⏳ Push to GitHub
4. ⏳ Create feature branch for ScienceComms integration

---

**Document Version**: 1.0  
**Author**: Claude AI  
**Purpose**: Pre-implementation state capture for ScienceComms upgrade  
