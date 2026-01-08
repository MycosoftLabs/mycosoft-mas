# 🎉 System Ready - MycoBrain Firmware Flash Guide

**Date**: January 8, 2026  
**Status**: Website & Device Manager Online, Firmware Ready for COM7

---

## ✅ Current System Status

| Service | Port | Status |
|---------|------|--------|
| **Mycosoft Website** | 3002 | 🟢 RUNNING |
| **MycoBrain Service** | 8003 | 🟢 RUNNING |
| **Device Manager** | Web UI | 🟢 WORKING |
| **Board on COM1** | — | 🟢 CONNECTED (showing in Device Manager) |
| **New Board on COM7** | — | ⚠️ READY TO FLASH |

### Access Points:
- **Website**: http://localhost:3002
- **Device Manager**: http://localhost:3002/natureos/devices
- **MycoBrain API**: http://localhost:8003

---

## 🚀 Next Step: Flash COM7 Board

### Firmware Location:
```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\firmware\MycoBrain_DeviceManager\MycoBrain_DeviceManager.ino
```

### What This Firmware Is:
- **Based on**: Dec 29 working firmware (MycoBrain_NeoPixel_Fixed)
- **Features**: FastLED NeoPixel, CLI commands, I2C scanning, BME688 support, sound effects
- **Compatible**: Works as bare board (no sensors) or with dual BME688 sensors
- **Protocol**: CLI text commands (compatible with MycoBrain service)

---

## ⚙️ Arduino IDE Settings (MEMORIZE THESE)

Open Arduino IDE and configure **Tools** menu:

```
Board: ESP32S3 Dev Module
USB CDC on boot: Enabled ✓         ← CRITICAL: Must be Enabled (not Disabled)
USB DFU on boot: Enabled
USB Mode: Hardware CDC and JTAG
JTAG Adapter: Integrated USB JTAG  
PSRAM: OPI PSRAM
CPU Frequency: 240 MHz
Flash Mode: QIO 80MHz
Flash Size: 16MB (128Mb)
Partition Scheme: 16M Flash (3MB APP/9.9MB FATFS)  ← Exact partition scheme
Upload Speed: 921600
Port: COM7
```

### Install Required Libraries:

**Tools → Manage Libraries** → Search and Install:
1. **FastLED** (for NeoPixel control)
2. **ArduinoJson** (if needed for future JSON support)
3. Wire (built-in)

---

## 📝 Flash Steps

1. **Open Arduino IDE**

2. **Set Board**: Tools → Board → ESP32 Arduino → ESP32S3 Dev Module

3. **Configure ALL Settings** from the table above

4. **Open Firmware**: File → Open → `firmware\MycoBrain_DeviceManager\MycoBrain_DeviceManager.ino`

5. **Verify**: Click ✓ button (should compile without errors)

6. **Select Port**: Tools → Port → COM7

7. **Upload**: Click → button

8. **Wait**: ~30 seconds for upload + verification

---

## ✅ Verification Tests

### Test 1: Serial Monitor

1. **Tools → Serial Monitor** (baud: 115200)
2. You should see boot messages:

```
====================================================================
  MycoBrain Device Manager Edition
  Mycosoft ESP32-S3
====================================================================
```

### Test 2: CLI Commands

Type in Serial Monitor:

| Command | Expected Result |
|---------|-----------------|
| `help` | List of commands |
| `status` | Device info, uptime, I2C count |
| `scan` | I2C devices (0 for bare board) |
| `led rgb 255 0 0` | LED turns RED |
| `led rgb 0 255 0` | LED turns GREEN |
| `led rgb 0 0 255` | LED turns BLUE |
| `coin` | Coin sound effect |
| `morgio` | SuperMorgIO jingle |

### Test 3: Device Manager Integration

1. Go to: http://localhost:3002/natureos/devices
2. Click **Refresh Ports** button
3. You should see **COM7** in the list
4. Click **COM7** button to connect
5. Board should appear with:
   - Node ID
   - Uptime
   - I2C status (0 devices for bare board)
   - Sensors tab showing "No peripherals detected"

### Test 4: Web Control

From Device Manager interface:
- Go to **Controls** tab
- Test LED color picker
- Test buzzer/sound buttons
- Verify LED changes color
- Verify buzzer plays sounds

---

## 🔧 Hardware Configuration

### Current Board (Bare):
- ✅ ESP32-S3 microcontroller
- ✅ SK6805 NeoPixel on GPIO15
- ✅ Buzzer on GPIO16
- ✅ MOSFET outputs on GPIO12, GPIO13, GPIO14
- ❌ NO sensors connected yet

### When BME688 Sensors Are Added:

| Sensor | I2C Address | Modification Required |
|--------|-------------|----------------------|
| **AMB** (Ambient) | 0x77 | None (default) |
| **ENV** (Environment) | 0x76 | **Solder bridge required** |

**See**: `docs/BME688_DUAL_SENSOR_SETUP.md` for solder bridge instructions

---

## 🐛 Troubleshooting

### "Compilation failed"
- Install FastLED library: Tools → Manage Libraries → FastLED
- Check ESP32 board package is version 2.0.13

### "Upload failed"
- Verify COM7 is selected
- Try holding BOOT button while clicking Upload
- Disconnect/reconnect USB cable
- Check Device Manager shows COM7

### "Board not detected after upload"
- **USB CDC on boot** must be **Enabled** (most common mistake)
- Try pressing RESET button
- Replug USB cable

### "Bootloop" (board keeps restarting)
- This bare board firmware should NOT bootloop
- If it does: check power supply (use powered USB hub)
- Brownout is disabled in firmware

### "LED doesn't work"
- Verify FastLED library is installed
- Check GPIO15 is connected to NeoPixel
- Try: `led rgb 255 255 255` for white

### "Buzzer doesn't work"
- GPIO16 connection
- Must be **passive** buzzer (not active)
- Try: `beep 1000 200`

---

## 📚 Firmware Commands Reference

### General:
- `help` - Show commands
- `status` - Full device status
- `scan` - I2C bus scan
- `poster` - Show banner

### LED Control:
- `led mode state` - Auto LED (default, green pulse)
- `led mode manual` - Manual control
- `led mode off` - Turn off
- `led rgb <r> <g> <b>` - Set color (0-255)

### Buzzer:
- `beep` - Default beep
- `beep <freq> <ms>` - Custom beep
- `coin` - Mario coin sound
- `bump` - Bump sound
- `power` - Power-up sound
- `1up` - 1-Up sound
- `morgio` - SuperMorgIO boot jingle

### Output:
- `fmt json` - JSON output (for Device Manager)
- `fmt lines` - Human-readable output (for Serial Monitor)
- `live on/off` - Toggle live telemetry

### Advanced:
- `i2c <sda> <scl> [hz]` - Change I2C pins (if needed)
- `reboot` - Restart device
- `dbg on/off` - Debug mode

---

## 🎯 Success Checklist

After flashing, verify:

- [ ] Serial Monitor shows boot banner
- [ ] `status` command works
- [ ] `scan` command returns (0 devices expected for bare board)
- [ ] `led rgb 255 0 0` makes LED red
- [ ] `coin` plays sound
- [ ] Device Manager shows COM7 in port list
- [ ] Can connect to board from Device Manager
- [ ] LED controls work from web interface
- [ ] Buzzer sounds work from web interface

---

## 📖 Additional Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Hardware Config | `docs/MYCOBRAIN_HARDWARE_CONFIG.md` | Pin mappings, Arduino settings |
| BME688 Setup | `docs/BME688_DUAL_SENSOR_SETUP.md` | Dual sensor modification guide |
| Flash Instructions | `FLASH_MYCOBRAIN_NOW.md` | This guide |
| Ngrok Setup | `docs/SHARING_WITH_NGROK.md` | Share with Claude Desktop/Garret |

---

## 🌐 Sharing with Claude Desktop & Garret

Once the board is working, you can expose it via ngrok:

```powershell
# Start ngrok tunnels
.\scripts\start_ngrok_tunnels.ps1 -All

# Or use the quick-start batch file
.\scripts\ngrok-start.bat
```

This will create public URLs like:
- `https://abc123.ngrok-free.app` → Your website
- `https://def456.ngrok-free.app` → MycoBrain API

Share these URLs and Claude Desktop or Garret can interact with your MycoBrain boards remotely!

---

## 🎉 What Happens Next

1. **Flash the board** (follow steps above)
2. **Test LED & buzzer** (Serial Monitor + Device Manager)
3. **When ready to add sensors**:
   - Modify one BME688 to address 0x76 (solder bridge)
   - Connect both BME688s to I2C
   - Upgrade to full BSEC2 firmware
   - Get temperature, humidity, IAQ readings

---

**Ready to flash! Open Arduino IDE and let's get this board working!** 🍄
