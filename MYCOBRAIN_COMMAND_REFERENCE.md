# MycoBrain Command Reference

**Last Updated:** 2025-12-28  
**Device:** MycoBrain V1 (Side-A on COM4)

## Command Testing Results

All commands tested successfully send to device (HTTP 200), but device responses are `null`, indicating:
- ✅ Commands are being sent correctly
- ❌ Device firmware may not be responding
- ⚠️ Device may need initialization or firmware update

## Supported Commands (from MDP v1 Spec)

### Core Commands

#### `i2c_scan`
Scan I2C bus for connected sensors.

**Request:**
```json
{
  "command": {"cmd": "i2c_scan"},
  "use_mdp": false
}
```

**Expected Response:** List of I2C addresses (e.g., `[0x76, 0x68]` for BME688 sensors)

---

#### `read_sensor`
Read data from a specific sensor.

**Request:**
```json
{
  "command": {"cmd": "read_sensor", "sensor_id": 0},
  "use_mdp": false
}
```

**Parameters:**
- `sensor_id` (int): Sensor index or I2C address

---

#### `set_telemetry_interval`
Set telemetry transmission interval.

**Request:**
```json
{
  "command": {"cmd": "set_telemetry_interval", "interval_seconds": 10},
  "use_mdp": false
}
```

**Parameters:**
- `interval_seconds` (int): Telemetry interval in seconds

---

#### `set_mosfet`
Control MOSFET outputs.

**Request:**
```json
{
  "command": {"cmd": "set_mosfet", "mosfet_index": 0, "state": true},
  "use_mdp": false
}
```

**Parameters:**
- `mosfet_index` (int): MOSFET index (0-3)
- `state` (bool): True = ON, False = OFF

---

#### `reset`
Reset Side-A MCU.

**Request:**
```json
{
  "command": {"cmd": "reset"},
  "use_mdp": false
}
```

---

### Device Information Commands

#### `ping`
Test device connectivity.

**Request:**
```json
{
  "command": {"cmd": "ping"},
  "use_mdp": false
}
```

**Expected Response:** `{"status": "ok"}` or similar

---

#### `status`
Get device status.

**Request:**
```json
{
  "command": {"cmd": "status"},
  "use_mdp": false
}
```

**Expected Response:** Device status information

---

#### `get_mac`
Get device MAC address.

**Request:**
```json
{
  "command": {"cmd": "get_mac"},
  "use_mdp": false
}
```

**Expected Response:** MAC address string

---

#### `get_version`
Get firmware version.

**Request:**
```json
{
  "command": {"cmd": "get_version"},
  "use_mdp": false
}
```

**Expected Response:** Firmware version string

---

### Peripheral Commands (May Not Be Supported)

These commands are sent successfully but may not be implemented in firmware:

#### `neopixel` / `set_neopixel`
Control NeoPixel LEDs.

**Request:**
```json
{
  "command": {"cmd": "neopixel", "r": 255, "g": 0, "b": 0, "brightness": 128},
  "use_mdp": false
}
```

**Parameters:**
- `r` (int): Red value (0-255)
- `g` (int): Green value (0-255)
- `b` (int): Blue value (0-255)
- `brightness` (int): Brightness (0-255)

**Note:** Device may return "Unknown peripheral" error if not implemented.

---

#### `buzzer` / `play_buzzer`
Control buzzer.

**Request:**
```json
{
  "command": {"cmd": "buzzer", "frequency": 1000, "duration": 500},
  "use_mdp": false
}
```

**Parameters:**
- `frequency` (int): Frequency in Hz (200-5000)
- `duration` (int): Duration in milliseconds

**Note:** Device may return "Unknown peripheral" error if not implemented.

---

## Command Format

### JSON Format (Current)
```json
{
  "command": {
    "cmd": "command_name",
    "param1": "value1",
    "param2": "value2"
  },
  "use_mdp": false
}
```

### MDP Format (Future)
```json
{
  "command": {
    "command_type": "command_name",
    "parameters": {
      "param1": "value1",
      "param2": "value2"
    }
  },
  "use_mdp": true
}
```

## API Endpoints

### Send Command
```
POST http://localhost:8003/devices/{device_id}/command
```

### Check Device Status
```
GET http://localhost:8003/devices/{device_id}/status
```

### Get Telemetry
```
GET http://localhost:8003/devices/{device_id}/telemetry
```

## Testing Script

Use `scripts/test_mycobrain_commands.py` to test all commands:

```bash
python scripts/test_mycobrain_commands.py
```

## Current Issues

1. **No Device Responses:** All commands return `null` response
   - Commands are sent successfully (HTTP 200)
   - Device may not be processing commands
   - May need firmware update or initialization

2. **No Telemetry:** Device not sending telemetry packets
   - Service is listening for telemetry
   - Device may need `set_telemetry_interval` command first
   - May need firmware update

3. **Peripheral Commands:** NeoPixel and Buzzer may not be implemented
   - Commands send successfully
   - Device may return "Unknown peripheral" error
   - Check firmware documentation

## Recommendations

1. **Verify Firmware Version**
   - Check if firmware supports all commands
   - Update firmware if needed

2. **Test with Serial Monitor**
   - Connect directly via serial monitor
   - Verify device is responding to commands
   - Check device logs/console

3. **Initialize Device**
   - Send `set_telemetry_interval` command
   - Wait for telemetry to start
   - Verify I2C sensors are detected

4. **Check Device Logs**
   - Monitor serial output
   - Look for error messages
   - Verify command parsing

## Next Steps

1. ✅ Document all command names
2. ✅ Test all commands via API
3. ⏳ Verify device firmware version
4. ⏳ Test telemetry transmission
5. ⏳ Update firmware if needed
6. ⏳ Test peripheral commands (NeoPixel, Buzzer)

