# ScienceComms Firmware Analysis

## Why ScienceComms Broke the Board

### Issue 1: PSRAM Configuration
The ScienceComms platformio.ini had this commented out:
```
; board_build.arduino.memory_type = qio_opi  # DISABLED - causes crashes
```

The MycoBrain hardware requires **OPI PSRAM** to be properly configured. Without it, or with incorrect settings, the board can brownout or crash.

**Fix in DeviceManager firmware**: Uses Arduino IDE with explicit PSRAM: OPI PSRAM setting.

### Issue 2: Wrong NeoPixel Library
ScienceComms uses NeoPixelBus:
```cpp
#include <NeoPixelBus.h>
NeoPixelBus<NeoGrbFeature, Neo800KbpsMethod> strip(1, NEOPIXEL_PIN);
```

The SK6805 NeoPixel on MycoBrain works with **Adafruit_NeoPixel** library, not NeoPixelBus.

**Fix in DeviceManager firmware**: 
```cpp
#include <Adafruit_NeoPixel.h>
Adafruit_NeoPixel pixels(PIXEL_COUNT, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
```

### Issue 3: tone() Function Not Working
ScienceComms uses:
```cpp
tone(BUZZER_PIN, 1000, 200);
```

The ESP32-S3 doesn't have a native `tone()` implementation. It needs to use the `ledc` peripheral for PWM.

**Fix in DeviceManager firmware**:
```cpp
ledcSetup(BUZZER_LEDC_CHANNEL, 2000, BUZZER_LEDC_RESOLUTION);
ledcAttachPin(BUZZER_PIN, BUZZER_LEDC_CHANNEL);
ledcWriteTone(BUZZER_LEDC_CHANNEL, freq);
```

### Issue 4: USB CDC Configuration
ScienceComms platformio.ini sets:
```
-DARDUINO_USB_MODE=1
-DARDUINO_USB_CDC_ON_BOOT=1
```

But may not match the Arduino IDE settings needed for proper USB-JTAG debugging.

**Fix in DeviceManager firmware**: Use Arduino IDE with:
- USB CDC on boot: Enabled
- USB DFU on boot: Enabled  
- USB Mode: Hardware CDC and JTAG
- JTAG Adapter: Integrated USB JTAG

### Issue 5: No BME Sensor Fallback
ScienceComms may have tried to initialize BSEC2 or BME688 sensors without proper error handling, causing crashes when no sensors are connected.

**Fix in DeviceManager firmware**: Sensor initialization is optional and has proper error handling.

## Working Arduino IDE Settings

```
Board: ESP32-S3 Dev Module
USB CDC on Boot: Enabled
USB DFU on Boot: Enabled
USB Firmware MSC on Boot: Disabled
USB Mode: Hardware CDC and JTAG
JTAG Adapter: Integrated USB JTAG
PSRAM: OPI PSRAM
CPU Frequency: 240 MHz
Flash Mode: QIO 80MHz
Flash Size: 16MB (128Mb)
Partition Scheme: 16M Flash (3MB APP / 9.9MB FATFS)
Upload Speed: 921600
```

## Current DeviceManager Firmware Features

### LED Control (Working)
- `led rgb <r> <g> <b>` - Set RGB color
- `led mode off|state|manual` - Set LED mode
- `led brightness <0-100>` - Set brightness (NEW)
- `led pattern solid|blink|breathe|rainbow|chase|sparkle` - Set pattern (NEW)

### Buzzer Control (Working)
- `beep [freq] [ms]` - Play a tone
- `coin` - Coin pickup sound (NEW)
- `bump` - Bump sound (NEW)
- `power` - Power up sound (NEW)
- `1up` - Extra life sound (NEW)
- `morgio` / `melody` - SuperMorgio jingle (NEW)

### Status Commands (Working)
- `status` - Get device status
- `help` - Show commands
- `scan` / `i2c_scan` - Scan I2C bus

## Features Still Needed (Future)

1. **Optical Modem TX** - Camera OOK, Manchester encoding
2. **Acoustic Modem TX** - FSK audio transmission
3. **Machine Mode NDJSON** - Already partially implemented
4. **LoRa Communication** - Requires SX1262 hardware
5. **BLE** - Basic BLE advertising

## Recommendation

Use the **MycoBrain_DeviceManager** firmware with Arduino IDE (not PlatformIO) for stable operation. The firmware now supports all UI controls:

- ✅ LED RGB with brightness
- ✅ LED patterns (rainbow, blink, breathe, etc.)
- ✅ Buzzer tones with frequency control
- ✅ Sound presets (coin, bump, power, 1up, morgio)
- ✅ I2C peripheral scanning
- ⏳ Optical/Acoustic modem (future)

---
**Last Updated**: January 8, 2026
