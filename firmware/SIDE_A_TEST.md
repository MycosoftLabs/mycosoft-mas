# Side-A Testing Guide

## ✅ Current Status
- **Side-A uploaded successfully**
- **Both green LEDs ON** = Sensors detected and working! ✅
- **No sounds** = Need to test buzzer

## 🔍 Check Serial Monitor

### Open Serial Monitor
1. **Tools → Serial Monitor**
2. **Baud rate: 115200**
3. **Line ending: Both NL & CR** (or Newline)

### What You Should See
```json
{"type":"status","data":{"status":"ready","mac":"XX:XX:XX:XX:XX:XX","firmware":"1.0.0"}}
```

Then every 10 seconds, telemetry:
```json
{"temperature":23.5,"humidity":45.2,"pressure":1013.25,"gas_resistance":50000,...}
```

## 🧪 Test Commands

### Test Buzzer
Send this in Serial Monitor:
```json
{"cmd":"buzzer","frequency":1000,"duration":500}
```

**Expected**: Should hear a beep

### Test Different Frequencies
```json
{"cmd":"buzzer","frequency":2000,"duration":300}
{"cmd":"buzzer","frequency":500,"duration":500}
```

### Test Series of Tones
Send multiple commands quickly:
```json
{"cmd":"buzzer","frequency":1000,"duration":200}
```
Wait 300ms, then:
```json
{"cmd":"buzzer","frequency":1500,"duration":200}
```
Wait 300ms, then:
```json
{"cmd":"buzzer","frequency":2000,"duration":300}
```

### Test NeoPixel
```json
{"cmd":"neopixel","r":255,"g":0,"b":0,"brightness":128}
```
**Expected**: Red LED

```json
{"cmd":"neopixel","r":0,"g":255,"b":0,"brightness":128}
```
**Expected**: Green LED

```json
{"cmd":"neopixel","r":0,"g":0,"b":255,"brightness":128}
```
**Expected**: Blue LED

### Test Status
```json
{"cmd":"status"}
```

### Test I2C Scan
```json
{"cmd":"i2c_scan"}
```
**Expected**: Should show 0x76 and 0x77

## 🔧 If Buzzer Doesn't Work

### Check Pin Configuration
The buzzer pin is set to **16**. If your board uses a different pin:
1. Check your board schematic
2. Update `BUZZER_PIN` in the code
3. Re-upload

### Test Buzzer Directly
Try this simpler test - modify the code temporarily:
```cpp
void setup() {
  // ... existing code ...
  pinMode(16, OUTPUT);
  tone(16, 1000, 500);  // Direct test
}
```

## 📊 Verify Sensors

### Check Telemetry
Wait 10 seconds after upload, you should see telemetry with:
- `temperature`
- `humidity`
- `pressure`
- `gas_resistance`
- `iaq` (if BSEC is working)

### Read Individual Sensor
```json
{"cmd":"read_sensor","sensor_id":0}
```
**Expected**: AMB sensor data

```json
{"cmd":"read_sensor","sensor_id":1}
```
**Expected**: ENV sensor data

## 🎯 Next Steps

1. **Check Serial Monitor** - see startup message
2. **Test buzzer** - send command above
3. **Test NeoPixel** - change colors
4. **Verify telemetry** - wait for auto-send
5. **Upload Side-B** - then test routing

## 📝 Report Back

Please tell me:
1. **What do you see in Serial Monitor?**
2. **Does buzzer work?** (after sending command)
3. **Do you see telemetry?** (every 10 seconds)
4. **Can you change NeoPixel colors?**

