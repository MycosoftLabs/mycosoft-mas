# MycoBrain Side-A — Arduino IDE Settings

These are the **known working settings** for the MycoBrain ESP32-S3 board.

## Board Configuration

| Setting | Value |
|---------|-------|
| **Board** | ESP32S3 Dev Module |
| **USB CDC On Boot** | Enabled |
| **USB DFU On Boot** | Enabled (requires USB OTG mode) |
| **USB Firmware MSC On Boot** | Disabled |
| **USB Mode** | Hardware CDC and JTAG |
| **JTAG Adapter** | Integrated USB JTAG |
| **PSRAM** | OPI PSRAM |
| **CPU Frequency** | 240 MHz |
| **Core Debug Level** | None |
| **Arduino Runs On** | Core 1 |
| **Events Run On** | Core 1 |
| **Flash Mode** | QIO @ 80 MHz |
| **Flash Size** | 16 MB |
| **Partition Scheme** | 16MB Flash, 3MB App / 9.9MB FATFS |
| **Upload Speed** | 921600 |
| **Erase All Flash Before Upload** | Disabled |

## Hardware Notes

### Bridged Board
This firmware includes brownout detector disable code for boards with the diode removed and wire bridge modification.

### Pin Configuration (ESP32AB Workbook)
- **I2C SDA**: GPIO 5
- **I2C SCL**: GPIO 4
- **I2C Frequency**: 100 kHz

- **RGB LED (PWM)**:
  - Red: GPIO 12
  - Green: GPIO 13
  - Blue: GPIO 14

- **Buzzer**: GPIO 16

- **Analog Inputs**: GPIO 6, 7, 10, 11

## Upload Instructions

1. Open `MycoBrain_SideA_Complete.ino` in Arduino IDE
2. Apply all settings from the table above
3. Select the correct COM port (look for "USB Serial Device" with VID 0x303A)
4. Click Upload

## Protocol

The firmware speaks **JSONL** (newline-delimited JSON) over USB CDC at 115200 baud.

### Commands (simple format)
```json
{"cmd":"ping"}
{"cmd":"get_mac"}
{"cmd":"get_version"}
{"cmd":"status"}
{"cmd":"i2c_scan"}
{"cmd":"set_telemetry_interval","ms":5000}
{"cmd":"led","mode":"manual","r":50,"g":0,"b":0}
{"cmd":"beep","freq":1000,"ms":100}
{"cmd":"config"}
{"cmd":"help"}
{"cmd":"reboot"}
```

### Commands (ESP32AB workbook format)
```json
{"type":"cmd","id":"c-001","op":"status"}
{"type":"cmd","id":"c-002","op":"i2c.scan"}
{"type":"cmd","id":"c-003","op":"telemetry.period","period_ms":1000}
```

### Telemetry Output
The firmware emits telemetry every 2 seconds (configurable):
```json
{"type":"tele","seq":123,"t_ms":45678,"node":"A-XX:XX:XX:XX:XX:XX","uptime_s":45,...}
```

Fields include:
- `temperature`, `humidity`, `pressure`, `gas_resistance` (null when sensors unplugged)
- `i2c_addresses` (array of detected I2C device addresses)
- `firmware_version`, `uptime_seconds`
- `mosfet_states`, `ai1_voltage` ... `ai4_voltage` (placeholders)

## LED State Machine

| Color | Meaning |
|-------|---------|
| Blue pulse | Booting |
| Blue breathing | Initializing |
| Green pulse | OK, sensors detected |
| Yellow | Warning (no sensors but running) |
| Red blink | Error |

## Troubleshooting

### Board not showing up as COM port
1. Try a different USB cable (must support data, not just charging)
2. Plug directly into PC (not through a hub)
3. Check Device Manager for "USB Serial Device" entries

### Boot loop / brownout
The bridged board modification should be handled by the firmware's brownout disable code. If still looping:
1. Use a powered USB hub or different USB port
2. Ensure BME688 sensors are disconnected if testing basic functionality

### Upload fails with "No serial data received"
1. Unplug the USB cable
2. Hold the BOOT button on the ESP32-S3
3. Plug in the USB cable while holding BOOT
4. Wait 2 seconds, then release BOOT
5. Click Upload immediately

