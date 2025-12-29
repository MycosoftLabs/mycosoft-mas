# Testing Side-A Firmware

## ✅ Upload Successful!
- **Port**: COM7
- **MAC Address**: 10:b4:1d:e3:3b:c4
- **Firmware**: Garrett's working BSEC2 dual BME688 firmware

## How to Test

### 1. Open Serial Monitor
- **Port**: COM7
- **Baud Rate**: 115200
- **Line Ending**: Both NL & CR

### 2. Press RESET Button
- Press the RESET button on Side-A board
- You should see the SuperMorgIO POST screen and boot jingle!

### 3. Test Commands

Type these commands in Serial Monitor:

#### Basic Commands
- `help` - Show all available commands
- `status` - Check sensor status and readings
- `scan` - I2C scan to see connected devices

#### LED Test
- `led rgb 255 0 0` - Red LED
- `led rgb 0 255 0` - Green LED
- `led rgb 0 0 255` - Blue LED
- `led rgb 255 255 0` - Yellow LED
- `led mode state` - Auto LED based on sensor status

#### Buzzer Test
- `coin` - Play coin sound
- `bump` - Play bump sound
- `power` - Play power-up sound
- `1up` - Play 1-up sound
- `morgio` - Play full SuperMorgIO boot jingle

#### Sensor Test
- `status` - See all sensor readings
- `live on` - Enable periodic live output
- `live off` - Disable periodic output
- `fmt json` - Switch to JSON output format
- `fmt lines` - Switch back to human-readable format

### 4. Expected Output

When you press RESET, you should see:
```
====================================================================
  SuperMorgIO
  Mycosoft ESP32AB
====================================================================
   ###############################
   #                             #
   #      _   _  ____  ____      #
   #     | \ | ||  _ \|  _ \\     #
   ...
--------------------------------------------------------------------
  Commands: help | poster | morgio | coin | bump | power | 1up
  LED: led mode off|state|manual  | led rgb <r> <g> <b>
--------------------------------------------------------------------
```

Then sensor initialization:
```
I2C: SDA=5 SCL=4 @ 100000 Hz
I2C scan:
  found: 0x76
  found: 0x77
--- BME ID probe @ 0x77 ---
  #1 chip_id: OK 0x61 | variant_id: OK 0x01
...
[AMB] begin OK
[ENV] begin OK
```

### 5. Verify Sensors

Type `status` and you should see:
- **AMB sensor** at 0x77: Temperature, Humidity, Pressure, Gas, IAQ
- **ENV sensor** at 0x76: Temperature, Humidity, Pressure, Gas
- **LED status**: Should be GREEN if both sensors working

### 6. Test LED
- Type: `led rgb 0 255 0`
- LED should turn green
- Type: `led mode state` to return to auto mode

### 7. Test Buzzer
- Type: `coin`
- Should hear coin sound
- Type: `morgio` for full jingle

## Troubleshooting

### No Output in Serial Monitor
- Check baud rate is 115200
- Press RESET button on board
- Check USB cable is connected
- Try closing and reopening Serial Monitor

### Sensors Not Detected
- Check I2C connections (SDA=5, SCL=4)
- Type `scan` to see what I2C devices are found
- Check sensor power connections

### LED Not Working
- Type `led mode manual` then `led rgb 255 0 0` (red)
- If no LED, check pin connections (12, 13, 14)

### Buzzer Not Working
- Type `coin` - should hear sound
- Check buzzer pin connection (pin 16)

## Next Steps

Once Side-A is working:
1. Test all sensors (`status`)
2. Test LED colors
3. Test buzzer sounds
4. Then we can integrate with MycoBrain service

