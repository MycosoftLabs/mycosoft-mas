# MycoBrain Firmware Quick Start

## Quick Upload Guide

### Step 1: Install Arduino IDE & ESP32 Support

1. Download Arduino IDE: https://www.arduino.cc/en/software
2. Open Arduino IDE → File → Preferences
3. Add to "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Tools → Board → Boards Manager
5. Search "ESP32" → Install "esp32 by Espressif Systems"

### Step 2: Install Libraries

1. Sketch → Include Library → Manage Libraries
2. Install:
   - **ArduinoJson** (by Benoit Blanchon)
   - **Adafruit BME680 Library** (by Adafruit)
   - **FastLED** (by Daniel Garcia)

### Step 3: Upload Side-A Firmware

1. Open `MycoBrain_SideA/MycoBrain_SideA.ino`
2. Tools → Board → ESP32 Arduino → **ESP32S3 Dev Module**
3. Tools → Port → Select your Side-A port (e.g., COM4)
4. Tools → Upload Speed → **921600**
5. Click **Upload** button (→)

### Step 4: Upload Side-B Firmware

1. Open `MycoBrain_SideB/MycoBrain_SideB.ino`
2. Tools → Board → ESP32 Arduino → **ESP32S3 Dev Module**
3. Tools → Port → Select your Side-B port (e.g., COM5)
4. Tools → Upload Speed → **921600**
5. Click **Upload** button (→)

### Step 5: Test

1. Open Serial Monitor (Tools → Serial Monitor)
2. Set baudrate to **115200**
3. Send test command:
   ```json
   {"cmd":"ping"}
   ```
4. You should see:
   ```json
   {"type":"ping","data":{"status":"ok"}}
   ```

## Pin Configuration

If your board uses different pins, edit the `#define` statements at the top of each sketch.

### Side-A Pins
- I2C: SDA=21, SCL=22
- Analog: AI1=34, AI2=35, AI3=36, AI4=39
- MOSFET: 25, 26, 27, 14
- NeoPixel: 4
- Buzzer: 32

### Side-B Pins
- UART to Side-A: RX=16, TX=17
- Status LED: 2

## Common Issues

**"Board not found"**
- Install ESP32 board support (Step 1)

**"Library not found"**
- Install libraries (Step 2)

**"Upload failed"**
- Hold BOOT button while clicking Upload
- Try lower upload speed (115200)

**"No response"**
- Check baudrate (115200)
- Verify correct port selected
- Check wiring connections

## Next Steps

After uploading:
1. Connect to MycoBrain service
2. Test commands via API
3. Monitor telemetry
4. Check device status

See `README.md` for full documentation.

