# Installation Fixes for Arduino IDE

## Common Compilation Errors

### Error: "stray '#' in program" or "1#include"

**Problem:** Copy-paste issue when copying code into Arduino IDE.

**Solution:**
1. **Don't copy-paste directly** - Instead:
   - File → New to create new sketch
   - File → Open → Navigate to `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`
   - OR: Copy the entire file content carefully, ensuring no extra characters

2. **Check the first line** - Make sure it starts with `/*` not `1/*` or anything else

3. **Use File → Open** instead of copy-paste:
   ```
   File → Open → firmware/MycoBrain_SideA/MycoBrain_SideA.ino
   ```

### Error: "bme68x_read_fptr_t does not name a type"

**Problem:** BME680 library compatibility issue with ESP32-S3.

**Solutions:**

**Option 1: Update Library**
1. Sketch → Include Library → Manage Libraries
2. Search "Adafruit BME680"
3. Uninstall old version
4. Install latest version (2.0.0 or later)

**Option 2: Use BME680 (not BME688)**
If you have BME680 sensors instead:
- The code will work with BME680
- Library is more stable
- Change sensor initialization if needed

**Option 3: Make BME688 Optional**
If sensors aren't connected yet, you can comment out BME688 code temporarily:
```cpp
// Comment out these lines:
// #include <Adafruit_BME680.h>
// Adafruit_BME680 bme1;
// etc.
```

### Error: Library Not Found

**Required Libraries:**
1. **ArduinoJson** (by Benoit Blanchon) - v6.21.0 or later
2. **Adafruit BME680 Library** (by Adafruit) - Latest version
3. **FastLED** (by Daniel Garcia) - v3.5.0 or later

**Install:**
- Sketch → Include Library → Manage Libraries
- Search each library name
- Click Install

### Error: Board Not Found

**Solution:**
1. File → Preferences
2. Add to "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Tools → Board → Boards Manager
4. Search "ESP32" → Install "esp32 by Espressif Systems"
5. Tools → Board → ESP32 Arduino → **ESP32S3 Dev Module**

### Error: Upload Failed

**Solutions:**
1. **Hold BOOT button** while clicking Upload
2. **Lower upload speed**: Tools → Upload Speed → 115200
3. **Check USB cable** - Use data cable, not charge-only
4. **Install drivers** - CH340 or CP2102 drivers for USB-Serial

## Step-by-Step Upload (Clean Method)

### Method 1: Open File Directly (Recommended)

1. **Open Arduino IDE**
2. **File → Open**
3. Navigate to: `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`
4. Click Open
5. Install libraries if prompted
6. Select board: **ESP32S3 Dev Module**
7. Select port: Your Side-A port
8. Click **Upload**

### Method 2: Create New Sketch

1. **File → New** (creates new sketch)
2. **Delete all default code**
3. **Copy entire content** from `MycoBrain_SideA.ino`
4. **Paste carefully** - Check first line is `/*`
5. **Save As**: `MycoBrain_SideA`
6. Upload as above

## Verification

After upload, open Serial Monitor (115200 baud):
- Should see: `{"type":"status","data":{"status":"ready",...}}`
- LED should turn green
- Buzzer should beep once

## If Still Having Issues

1. **Check Arduino IDE version** - Use 1.8.19 or later
2. **Check ESP32 board package version** - Update if old
3. **Try PlatformIO** instead of Arduino IDE:
   ```bash
   cd firmware/MycoBrain_SideA
   pio run -t upload
   ```
4. **Check serial port** - Make sure correct port selected
5. **Check wiring** - Verify all connections

## Minimal Test Version

If libraries are causing issues, here's a minimal version without BME688:

```cpp
#include <Wire.h>
#include <ArduinoJson.h>

#define SERIAL_BAUD 115200

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1000);
  Serial.println("{\"status\":\"ready\"}");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    if (cmd.indexOf("ping") >= 0) {
      Serial.println("{\"type\":\"ping\",\"data\":{\"status\":\"ok\"}}");
    }
  }
  delay(10);
}
```

Upload this first to verify basic communication, then add features back.

