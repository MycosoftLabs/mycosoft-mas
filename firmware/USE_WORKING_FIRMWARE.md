# Using Garrett's Working Firmware

## ✅ Status
**Garrett's working firmware has been copied to `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`**

This is the **exact firmware that was working before** on your board.

## Files Copied
- ✅ `MycoBrain_SideA.ino` - Main firmware sketch
- ✅ `bsec_selectivity.h` - BSEC configuration header

## Upload Instructions

### 1. Open in Arduino IDE
- Open `firmware/MycoBrain_SideA/MycoBrain_SideA.ino` in Arduino IDE

### 2. Board Settings
- **Board**: ESP32-S3 Dev Module
- **Port**: COM4 (or your Side-A port)
- **Upload Speed**: 921600 (or lower if issues)
- **CPU Frequency**: 240MHz
- **Flash Frequency**: 80MHz
- **Flash Mode**: QIO
- **Flash Size**: 4MB (or your board's size)
- **Partition Scheme**: Default 4MB with spiffs
- **Core Debug Level**: None
- **PSRAM**: Disabled (unless your board has PSRAM)

### 3. Put Device in Boot Mode
1. **Unplug USB** from Side-A
2. **Wait 10 seconds**
3. **Hold BOOT button**
4. **Plug USB back in** (keep holding BOOT)
5. **Hold BOOT for 5 seconds**
6. **Release BOOT**
7. **Wait 2 seconds**

### 4. Upload
- Click **Upload** in Arduino IDE
- Should upload successfully

### 5. Open Serial Monitor
- **Baud Rate**: 115200
- **Line ending**: Both NL & CR
- You should see the SuperMorgIO POST screen and boot jingle!

## Features
This firmware includes:
- ✅ Dual BME688 sensors (AMB @ 0x77, ENV @ 0x76)
- ✅ BSEC2 IAQ algorithm
- ✅ RGB LED indicators (state machine)
- ✅ Buzzer with retro game sounds
- ✅ Serial CLI commands
- ✅ Boot reliability fixes

## Commands Available
Type these in Serial Monitor:
- `help` - Show all commands
- `status` - Show sensor status
- `scan` - I2C scan
- `led rgb 255 0 0` - Set LED to red
- `morgio` - Play boot jingle
- `coin` - Play coin sound
- And many more!

## Next Steps
Once this is working:
1. Test sensors: `status` command
2. Test LED: `led rgb 0 255 0` (green)
3. Test buzzer: `coin` or `morgio`
4. Then we can integrate with MycoBrain service


