# 🚀 Flash MycoBrain to COM7 - Quick Guide

## Current Status ✅

| Component | Status |
|-----------|--------|
| **Mycosoft Website** | 🟢 Running on port 3002 |
| **MycoBrain Service** | 🟢 Running on port 8003 |
| **Device Manager** | 🟢 Working - showing COM1 device |
| **New Board (COM7)** | ⚠️ Needs firmware |

---

## 📁 Firmware Ready

**Location**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\firmware\MycoBrain_DeviceManager\MycoBrain_DeviceManager.ino`

**Version**: Dec 29 working firmware (Dual Mode with Machine Protocol)

---

## ⚡ Flash Instructions

### 1. Open Arduino IDE

Launch Arduino IDE on your Windows machine

### 2. Configure Board Settings

Go to **Tools** menu and set these EXACTLY:

```
Board: ESP32S3 Dev Module
USB CDC on boot: Enabled ✓        <-- MUST BE ENABLED
USB DFU on boot: Enabled
USB Mode: Hardware CDC and JTAG
JTAG Adapter: Integrated USB JTAG
PSRAM: OPI PSRAM
CPU Frequency: 240 MHz
Flash Mode: QIO 80MHz
Flash Size: 16MB (128Mb)
Partition Scheme: 16M Flash (3MB APP/9.9MB FATFS)
Upload Speed: 921600
Port: COM7                          <-- Your new board
```

### 3. Install Required Libraries

**Tools → Manage Libraries** and install:
- **ArduinoJson** by Benoit Blanchon
- **FastLED** by Daniel Garcia
- **Wire** (built-in)

### 4. Open Firmware

**File → Open →** `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\firmware\MycoBrain_DeviceManager\MycoBrain_DeviceManager.ino`

###5. Upload

1. Click **Verify** (✓) to compile
2. Click **Upload** (→) to flash
3. Wait ~30 seconds

### 6. Test in Serial Monitor

1. **Tools → Serial Monitor**
2. Set baud rate: **115200**
3. You should see:

```
====================================================================
  MycoBrain Device Manager Edition
  Mycosoft ESP32-S3
====================================================================
```

### 7. Test Commands

Type in Serial Monitor:

```
help             ← Show commands
status           ← Device info
scan             ← Scan I2C (will show 0 devices on bare board)
led rgb 255 0 0  ← Red LED
coin             ← Test buzzer
```

### 8. Test in Device Manager

1. Go to: http://localhost:3002/natureos/devices
2. Click **Refresh Ports**
3. Click **COM7** button to connect
4. You should see the board appear with telemetry
5. Test LED and buzzer from web interface

---

## 🎯 What This Firmware Does

### ✅ Works NOW (Bare Board):
- NeoPixel LED control (SK6805 on GPIO15)
- Buzzer control with sound effects
- I2C bus scanning
- Machine Mode Protocol (JSON commands)
- Device Manager integration
- Telemetry streaming

### 🔮 Will Work LATER (When Sensors Added):
- Dual BME688 detection (0x77 and 0x76)
- Temperature/humidity/pressure readings
- Air quality (IAQ, CO2eq, VOC)
- BSEC2 algorithm processing

---

## 🔧 Important Notes

### USB CDC Setting:
- Chris's original had "USB CDC on boot: **Disabled**"
- We need it **Enabled** for proper Device Manager communication
- This is THE critical setting that's different

### BME688 Dual Sensor (Future):
When you add BME688 sensors:
1. One sensor stays at address 0x77 (AMB - ambient)
2. Other sensor modified to 0x76 (ENV - environment)
3. Garret's modification: solder the ADR/ADDR jumper on ONE BME688
4. Without this mod, both sensors conflict and board won't work

### Bootloop Prevention:
- BSEC library can cause bootloops if not initialized properly
- This bare board firmware avoids BSEC until sensors are added
- Brownout detection is disabled for bridged boards

---

## 🎉 Success Criteria

After flashing, you should be able to:
- [ ] See boot messages in Serial Monitor
- [ ] Send `status` command and get JSON response
- [ ] Control LED from Serial Monitor: `led rgb 0 0 255`
- [ ] Hear buzzer sounds: `coin`, `bump`, `morgio`
- [ ] See board in Device Manager at http://localhost:3002/natureos/devices
- [ ] Control LED from Device Manager web interface
- [ ] See "0 peripherals" in scan (expected for bare board)

---

## 📞 Quick Reference

| Task | Command/URL |
|------|-------------|
| Open Arduino IDE | Start Menu → Arduino IDE |
| Firmware location | `firmware\MycoBrain_DeviceManager\MycoBrain_DeviceManager.ino` |
| COM Port | COM7 |
| Serial Monitor Baud | 115200 |
| Device Manager URL | http://localhost:3002/natureos/devices |
| Test LED | `led rgb 255 0 0` |
| Test Buzzer | `coin` or `morgio` |

---

**Ready to flash! Open Arduino IDE and follow the steps above.** 🍄
