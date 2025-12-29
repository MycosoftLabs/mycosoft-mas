# MycoBrain Telemetry Analysis

**Date:** 2025-12-28  
**Device:** mycobrain-side-a-COM4  
**Status:** Connected but no telemetry received

## Current Status

### Service Status
- ✅ Device connected on COM4
- ✅ Serial port open
- ✅ Background reader thread running
- ❌ No telemetry data received

### Telemetry Endpoint Response
```json
{
  "status": "no_data",
  "device_id": "mycobrain-side-a-COM4",
  "message": "No telemetry received"
}
```

## Telemetry Reception Mechanism

The service uses a background thread (`_read_device_telemetry`) that:

1. **Continuously reads** from serial port
2. **Tries MDP protocol** first (COBS framing)
3. **Falls back to JSON lines** if MDP fails
4. **Caches telemetry** in `telemetry_cache[device_id]`

### MDP Protocol (Preferred)
- Looks for COBS frame delimiter (0x00)
- Decodes using `MDPDecoder`
- Parses `MDPTelemetry` objects
- Stores with sequence numbers

### JSON Fallback
- Looks for newline-delimited JSON
- Parses as dictionary
- Stores as raw telemetry

## Possible Issues

### 1. Device Not Sending Telemetry
**Symptoms:**
- No data in serial buffer (`ser.in_waiting == 0`)
- No telemetry in cache

**Possible Causes:**
- Device firmware not configured to send telemetry
- Telemetry interval not set
- Device in sleep mode
- Device waiting for initialization command

**Solution:**
```python
# Send telemetry interval command
POST /devices/mycobrain-side-a-COM4/command
{
  "command": {"cmd": "set_telemetry_interval", "interval_seconds": 10},
  "use_mdp": false
}
```

### 2. Protocol Mismatch
**Symptoms:**
- Data in buffer but not parsing correctly
- MDP decoder errors
- JSON parse errors

**Possible Causes:**
- Device sending different format
- COBS framing not matching
- CRC16 mismatch

**Solution:**
- Check service logs for decode errors
- Monitor raw serial data
- Verify firmware protocol version

### 3. Serial Communication Issue
**Symptoms:**
- Serial port open but no data
- Timeout errors
- Buffer not filling

**Possible Causes:**
- Wrong baudrate
- Flow control issues
- Device not powered
- USB connection issue

**Solution:**
- Verify baudrate (115200)
- Check USB connection
- Test with serial monitor

## Testing Telemetry

### Test 1: Check Serial Buffer
```python
# In service, check if data is arriving
if ser.in_waiting > 0:
    data = ser.read(ser.in_waiting)
    print(f"Received: {data}")
```

### Test 2: Enable Telemetry
```bash
# Send command to enable telemetry
curl -X POST http://localhost:8003/devices/mycobrain-side-a-COM4/command \
  -H "Content-Type: application/json" \
  -d '{"command":{"cmd":"set_telemetry_interval","interval_seconds":5},"use_mdp":false}'
```

### Test 3: Monitor Service Logs
```bash
# Check service output for telemetry reception
# Look for: "Received telemetry from {device_id}"
```

### Test 4: Direct Serial Test
```python
import serial
import time

ser = serial.Serial('COM4', 115200, timeout=2)
time.sleep(1)

# Send command to request telemetry
ser.write(b'{"cmd": "status"}\n')
time.sleep(2)

# Check for response
if ser.in_waiting > 0:
    response = ser.read(ser.in_waiting)
    print(f"Response: {response.decode('utf-8', errors='replace')}")
else:
    print("No response from device")

ser.close()
```

## Expected Telemetry Format

### MDP Telemetry (Preferred)
```
Frame: [COBS][Type:0x01][Sequence][Payload][CRC16][0x00]
Payload (JSON): {
  "ai1_voltage": 3.3,
  "ai2_voltage": 2.5,
  "temperature": 25.5,
  "humidity": 60.0,
  "pressure": 1013.25,
  "gas_resistance": 50000,
  "mosfet_states": [true, false, false, false],
  "i2c_addresses": [0x76, 0x68],
  "firmware_version": "1.0.0",
  "uptime_seconds": 3600
}
```

### JSON Telemetry (Fallback)
```json
{
  "temperature": 25.5,
  "humidity": 60.0,
  "pressure": 1013.25,
  "gas_resistance": 50000
}
```

## Recommendations

1. **Send Telemetry Interval Command**
   - Set interval to 5-10 seconds
   - Wait 10-15 seconds
   - Check if telemetry starts arriving

2. **Check Device Firmware**
   - Verify firmware version
   - Check if telemetry is enabled by default
   - Review firmware documentation

3. **Monitor Serial Output**
   - Use serial monitor to see raw device output
   - Verify device is sending data
   - Check data format

4. **Test with Simple Command**
   - Send `status` command
   - Check if device responds
   - Verify communication is working

5. **Check Service Logs**
   - Look for telemetry reception messages
   - Check for decode errors
   - Verify background thread is running

## Next Steps

1. ✅ Document telemetry mechanism
2. ⏳ Send `set_telemetry_interval` command
3. ⏳ Monitor service logs for telemetry
4. ⏳ Test with serial monitor
5. ⏳ Verify firmware telemetry support

