# Full MycoBrain Firmware Ready!

## ✅ Created Files

### Side-A (Sensor MCU)
- **File**: `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`
- **Based on**: Garrett's working BSEC2 implementation
- **Features**:
  - Dual BME688 sensors (AMB @ 0x77, ENV @ 0x76)
  - BSEC2 IAQ algorithm
  - JSON command interface
  - Telemetry transmission
  - I2C scanning
  - Analog inputs, MOSFET control, NeoPixel, Buzzer

### Side-B (Router MCU)
- **File**: `firmware/MycoBrain_SideB/MycoBrain_SideB.ino`
- **Features**:
  - UART communication with Side-A
  - Command routing (PC → Side-A)
  - Telemetry forwarding (Side-A → PC)
  - Connection monitoring
  - Status LED

## 📋 Upload Instructions

### Step 1: Upload Side-A
1. **Open**: `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`
2. **Board**: ESP32S3 Dev Module
3. **Port**: Your Side-A USB port (check which COM port)
4. **Upload Speed**: 921600
5. **Click Upload**

### Step 2: Upload Side-B
1. **Open**: `firmware/MycoBrain_SideB/MycoBrain_SideB.ino`
2. **Board**: ESP32S3 Dev Module
3. **Port**: Your Side-B USB port (different COM port)
4. **Upload Speed**: 921600
5. **Click Upload**

## 🔍 Verify Installation

### Side-A Serial Monitor (115200 baud)
You should see:
```json
{"type":"status","data":{"status":"ready","mac":"XX:XX:XX:XX:XX:XX","firmware":"1.0.0"}}
```

### Side-B Serial Monitor (115200 baud)
You should see:
```
=== MycoBrain Side-B (Router) ===
MAC: XX:XX:XX:XX:XX:XX
Firmware: 1.0.0
Waiting for Side-A connection...
Side-A connected
```

## 🧪 Test Commands

### Test Side-A (via Side-B or directly)
```json
{"cmd":"ping"}
{"cmd":"status"}
{"cmd":"i2c_scan"}
{"cmd":"set_telemetry_interval","interval_seconds":5}
```

### Test Controls
```json
{"cmd":"neopixel","r":255,"g":0,"b":0,"brightness":128}
{"cmd":"buzzer","frequency":1000,"duration":500}
{"cmd":"set_mosfet","mosfet_index":0,"state":true}
```

## 📊 Expected Behavior

### Side-A
- **Green LED**: Both sensors initialized and working
- **Telemetry**: Auto-sends every 10 seconds
- **Commands**: Responds to JSON commands

### Side-B
- **LED ON**: Side-A connected
- **LED OFF**: Side-A disconnected
- **Forwards**: All commands and telemetry

## 🔧 Configuration

### Side-A UART Pins (if needed)
In `MycoBrain_SideB.ino`, adjust if your board uses different pins:
```cpp
#define UART_RX 16  // Change if needed
#define UART_TX 17  // Change if needed
```

### Telemetry Interval
Default: 10 seconds
Change via command: `{"cmd":"set_telemetry_interval","interval_seconds":5}`

## 🎯 Next Steps

1. **Upload both firmwares**
2. **Open Serial Monitors** for both
3. **Test commands**
4. **Connect to MycoBrain service**
5. **Test in website dashboard**

## 📝 Notes

- **BSEC Config**: Uses `bsec_selectivity.h` if available
- **Pins**: Matches Garrett's working configuration
- **Compatibility**: Works with MycoBrain service JSON format
- **Error Handling**: Continues even if sensors fail

The firmware is ready to test on your working board!

