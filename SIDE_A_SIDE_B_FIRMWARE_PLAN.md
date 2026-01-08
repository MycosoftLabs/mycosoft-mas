# MycoBrain Dual-ESP Architecture - Firmware Plan
**Board**: MycoBrain V1 with 2x ESP32-S3  
**Architecture**: [GitHub - MycosoftLabs/mycobrain](https://github.com/MycosoftLabs/mycobrain)  

## 🎯 CONFIRMED ARCHITECTURE

### Side-A (ESP-1) - **SENSOR MCU** ✅ FLASHED
**Role**: Sensors, I2C scanning, analog sampling, MOSFET control  
**Firmware**: MycoBrain_ScienceComms ✅ Just flashed!  
**Port**: COM5 (primary USB-C port)  

**Capabilities**:
- ✅ BME688 sensor reading (I2C)
- ✅ I2C bus scanning
- ✅ Analog inputs (AI1-AI4)
- ✅ MOSFET outputs (AO1-AO3)
- ✅ NeoPixel LED control (GPIO15)
- ✅ Buzzer control (GPIO16)
- ✅ Optical TX (LED communication)
- ✅ Acoustic TX (buzzer communication)
- ✅ Machine Mode (NDJSON protocol)

**Commands Available**:
```
led rgb, led pattern, buzz tone, buzz pattern
optx start, aotx start, stim light, stim sound
periph scan, mode machine, status, help
```

### Side-B (ESP-2) - **ROUTER MCU** ⏳ NEEDS FLASHING
**Role**: UART↔LoRa routing, reliability, command channel  
**Firmware**: MycoBrain_SideB (needs to be flashed)  
**Port**: COM? (secondary USB-C port - UART-2)  

**Capabilities** (When Flashed):
- LoRa TX/RX (SX1262 radio)
- UART communication with Side-A
- Command routing A↔B
- ACK + retransmit logic
- Gateway integration

**Pin Mapping** (SX1262 LoRa):
```
SCK    → GPIO 9
MOSI   → GPIO 8  
MISO   → GPIO 12
NSS/CS → GPIO 13
DIO1   → GPIO 14
DIO2   → GPIO 11
BUSY   → GPIO 10
```

## 📋 CURRENT STATUS

| Component | Status | Firmware | Port | Notes |
|-----------|--------|----------|------|-------|
| **ESP Side-A** | ✅ Flashed | ScienceComms v1.0 | COM5 | All sensors & features working |
| **ESP Side-B** | ⏳ Not Flashed | Need MycoBrain_SideB | TBD | LoRa routing pending |
| **SX1262 LoRa** | ⏳ Inactive | Controlled by Side-B | SPI | Waiting for Side-B firmware |

## 🔧 SIDE-B FLASHING PLAN

### Step 1: Identify Side-B USB Port
```powershell
# Side-A is on COM5
# Side-B is on COM? (need to find)

# Scan for available ESP32 devices
mode  # List COM ports
# Look for second ESP32-S3 device
```

### Step 2: Flash Side-B Firmware
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_SideB
pio run -t upload --upload-port COM[X]
```

### Step 3: Verify Communication
```bash
# Side-A and Side-B should communicate via UART
# Side-B will forward telemetry to LoRa
# Side-B will route commands from LoRa to Side-A
```

## 🐛 PERIPHERALS ISSUE

**Problem**: Peripherals not showing up in UI  
**Root Cause**: API route `/api/mycobrain/[port]/peripherals` may have issues  

### Investigation Needed
1. Check if `/api/mycobrain/COM5/peripherals` returns 404
2. Verify route exists in Docker build  
3. Test peripheral scan command directly
4. Check NDJSON parsing

### Quick Test
```powershell
# Test peripheral scan via API
Invoke-RestMethod "http://localhost:3000/api/mycobrain/COM5/peripherals"

# Test direct command
$body = '{"command": {"cmd": "periph scan"}}'
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM5/command" -Method POST -Body $body -ContentType "application/json"
```

## 🎯 CURRENT ARCHITECTURE STATE

```
[Side-A ESP32-S3] ✅ ScienceComms Firmware
  ├─> COM5 USB ← MycoBrain Service (8003) ← Website (3000)
  ├─> GPIO15: NeoPixel LED
  ├─> GPIO16: Buzzer  
  ├─> GPIO4/5: I2C (BME688 sensors)
  ├─> GPIO6/7/10/11: Analog inputs
  └─> GPIO12/13/14: MOSFET outputs

[Side-B ESP32-S3] ⏳ NOT FLASHED YET
  ├─> COM?: USB (not identified yet)
  ├─> UART ← Side-A (internal communication)
  └─> SPI → SX1262 LoRa Module
       └─> 915MHz/868MHz radio (not active)

[SX1262 LoRa] ⏳ Waiting for Side-B
  └─> Long-range wireless (up to 10km)
```

## 🚀 NEXT STEPS

### Immediate (Now)
1. ✅ Side-A flashed with ScienceComms
2. ⏳ Test all new Side-A features
3. ⏳ Fix peripherals display issue
4. ⏳ Identify Side-B COM port
5. ⏳ Flash Side-B firmware

### Testing Priority
1. **Side-A Features** (Just flashed):
   - LED patterns (rainbow, chase, etc.)
   - Custom buzzer tones  
   - Optical TX
   - Acoustic TX (if working)
   - Peripherals scan

2. **Side-B Features** (After flashing):
   - LoRa TX/RX
   - UART communication with Side-A
   - Command routing
   - Gateway mode

---
**Status**: Side-A firmware upgraded ✅  
**Next**: Test Side-A features → Flash Side-B → Enable LoRa  
**Issue**: MycoBrain service needs restart with new firmware  


