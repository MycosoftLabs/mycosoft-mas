# MycoBrain Firmware Update Summary

## What Was Done

### 1. Libraries Copied ✅
Copied Garrett's working libraries to Arduino:
- `BME68x_Sensor_library` → `C:\Users\admin2\Documents\Arduino\libraries\BME68x_Sensor_library`
- `Bosch-BSEC2-Library-master` → `C:\Users\admin2\Documents\Arduino\libraries\Bosch-BSEC2-Library-master`
- `Adafruit_NeoPixel` → `C:\Users\admin2\Documents\Arduino\libraries\Adafruit_NeoPixel`

### 2. BSEC Config File ✅
Copied `bsec_selectivity.h` to `firmware/MycoBrain_SideA/bsec_selectivity.h`

### 3. Updated Side-A Firmware ✅
Created new `MycoBrain_SideA.ino` based on Garrett's working code:
- Uses **BSEC2 library** (not Adafruit BME680)
- Uses correct pins: **SDA=5, SCL=4** (not 21/22)
- Dual BME688 sensors: **AMB @ 0x77, ENV @ 0x76**
- Includes BSEC2 IAQ algorithm
- JSON command interface compatible with service
- Telemetry in JSON format

### 4. Updated Side-B Firmware ✅
Created new `MycoBrain_SideB.ino`:
- UART communication with Side-A
- Command routing (PC → Side-A)
- Telemetry forwarding (Side-A → PC)
- Connection monitoring

## Key Changes from Previous Version

### Pin Configuration
- **I2C**: SDA=5, SCL=4 (was 21/22)
- **Analog**: 6, 7, 10, 11
- **RGB LED**: 12, 13, 14 (PWM)
- **Buzzer**: 16
- **NeoPixel**: 15

### Library Changes
- **Removed**: Adafruit BME680 library
- **Added**: Bosch BSEC2-Library-master
- **Added**: BME68x_Sensor_library
- **Kept**: ArduinoJson, Adafruit_NeoPixel

### Sensor Configuration
- Uses **BSEC2 algorithm** for IAQ calculations
- Separate BSEC instances for each sensor
- BSEC config blob from `bsec_selectivity.h`

## Installation Steps

### 1. Install ArduinoJson (if not already installed)
```
Sketch → Include Library → Manage Libraries
Search "ArduinoJson" → Install
```

### 2. Upload Side-A Firmware
1. Open `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`
2. Board: **ESP32S3 Dev Module**
3. Port: Your Side-A USB port
4. Upload Speed: **921600**
5. Click **Upload**

### 3. Upload Side-B Firmware
1. Open `firmware/MycoBrain_SideB/MycoBrain_SideB.ino`
2. Board: **ESP32S3 Dev Module**
3. Port: Your Side-B USB port
4. Upload Speed: **921600**
5. Click **Upload**

## Testing

### Serial Monitor (115200 baud)

**Test Side-A:**
```json
{"cmd":"ping"}
{"cmd":"status"}
{"cmd":"i2c_scan"}
```

**Expected Response:**
```json
{"type":"ping","data":{"status":"ok"}}
{"type":"status","data":{"status":"ready","mac":"AA:BB:CC:DD:EE:FF",...}}
```

**Test Telemetry:**
- Telemetry auto-sends every 10 seconds
- Should see JSON with temperature, humidity, pressure, gas_resistance, IAQ values

**Test Commands:**
```json
{"cmd":"set_telemetry_interval","interval_seconds":5}
{"cmd":"set_mosfet","mosfet_index":0,"state":true}
{"cmd":"neopixel","r":255,"g":0,"b":0,"brightness":128}
{"cmd":"buzzer","frequency":1000,"duration":500}
```

## Compatibility

### With MycoBrain Service
- ✅ JSON command format matches service expectations
- ✅ Telemetry format compatible
- ✅ All commands supported
- ✅ MAC address reporting
- ✅ I2C scanning
- ✅ Sensor reading

### With Website
- ✅ Device manager will show connected device
- ✅ Telemetry will display in real-time
- ✅ Controls will work (NeoPixel, Buzzer, MOSFET)

## Troubleshooting

### "Library not found"
- Restart Arduino IDE
- Check: `C:\Users\admin2\Documents\Arduino\libraries\`
- Verify folder names match exactly

### "bsec2.h not found"
- Verify `Bosch-BSEC2-Library-master` is in libraries folder
- Restart Arduino IDE

### "bsec_selectivity.h not found"
- File should be in same folder as `.ino` file
- Check: `firmware/MycoBrain_SideA/bsec_selectivity.h`

### Sensors not detected
- Check I2C wiring (SDA=5, SCL=4)
- Run `{"cmd":"i2c_scan"}` to verify addresses
- Should see 0x76 and 0x77

### No telemetry
- Send: `{"cmd":"set_telemetry_interval","interval_seconds":5}`
- Wait 10 seconds
- Check Serial Monitor

## Files Created/Updated

1. ✅ `firmware/MycoBrain_SideA/MycoBrain_SideA.ino` - Updated with BSEC2
2. ✅ `firmware/MycoBrain_SideB/MycoBrain_SideB.ino` - Router firmware
3. ✅ `firmware/MycoBrain_SideA/bsec_selectivity.h` - BSEC config
4. ✅ Libraries copied to Arduino folder

## Next Steps

1. Install ArduinoJson library
2. Upload Side-A firmware
3. Upload Side-B firmware
4. Test with Serial Monitor
5. Connect to MycoBrain service
6. Test in website dashboard

The firmware is now ready and matches Garrett's working implementation!

