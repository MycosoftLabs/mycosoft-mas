# Test Side-A Standalone (Recommended)

## ✅ Current Status
- **Side-A**: Working on COM4 ✅
- **Side-B**: No power/LED ❌ (hardware issue)

## Good News!

**Side-A can work completely standalone!**

You don't need Side-B for:
- ✅ Sensor readings
- ✅ Buzzer control
- ✅ NeoPixel control
- ✅ MOSFET control
- ✅ I2C scanning
- ✅ Telemetry transmission
- ✅ MycoBrain service connection
- ✅ Website dashboard

## 🧪 Test Side-A Now

### Step 1: Connect to MycoBrain Service
1. **Start MycoBrain service**:
   ```powershell
   cd services/mycobrain
   python mycobrain_dual_service.py
   ```

2. **Connect to COM4**:
   - Service will detect Side-A
   - Will scan for sensors
   - Will start receiving telemetry

### Step 2: Test in Website
1. **Open**: http://localhost:3000/natureos/devices
2. **MycoBrain Devices tab**
3. **Should see**: Connected device on COM4
4. **Test controls**:
   - NeoPixel color picker
   - Buzzer button
   - MOSFET toggles

### Step 3: Verify Telemetry
- **Should see**: Temperature, humidity, pressure, gas resistance
- **Updates**: Every 10 seconds
- **IAQ values**: If BSEC2 is working

## 📋 Test Checklist

- [x] Side-A uploaded ✅
- [x] Serial commands work ✅
- [x] Green LEDs (sensors detected) ✅
- [ ] Buzzer tested
- [ ] NeoPixel tested
- [ ] Telemetry verified
- [ ] MycoBrain service connected
- [ ] Website dashboard working
- [ ] Side-B fixed (later)

## 🎯 What to Test

### Via Serial Monitor (COM4, 115200)
```json
{"cmd":"buzzer","frequency":1000,"duration":500}
{"cmd":"neopixel","r":255,"g":0,"b":0,"brightness":128}
{"cmd":"status"}
{"cmd":"i2c_scan"}
```

### Via MycoBrain Service
- Connect to COM4
- Should see device with sensors
- Telemetry should flow
- Controls should work

### Via Website
- Device should appear
- Telemetry should display
- Controls should work

## 🔧 Fix Side-B Later

Once Side-A is fully tested:
1. **Get working USB cable** for Side-B
2. **Check Side-B hardware** (might need repair)
3. **Upload Side-B firmware** when it's powered
4. **Test routing** between Side-A and Side-B

## 🚀 Ready to Test!

**Proceed with Side-A testing** - it's fully functional standalone!


