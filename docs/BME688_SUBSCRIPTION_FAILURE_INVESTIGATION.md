# BME688 Subscription Failure Investigation

**Date**: January 24, 2026  
**Status**: Investigation in Progress  
**Device**: ESP32-S3 on COM7 (mycobrain-COM7)  
**Sensors**: 2x BME688 (0x77 AMB, 0x76 ENV)

---

## Summary

Both BME688 sensors are detected and initialized successfully, but `updateSubscription()` calls are failing. This prevents the BSEC2 library from providing IAQ, CO2, VOC, and other calculated outputs.

---

## Current Status

| Sensor | Address | Detection | Begin | Config | Subscription | Status |
|--------|---------|-----------|-------|--------|--------------|--------|
| AMB | 0x77 | ✓ PASS | ✓ PASS | ? | ✗ FAIL | Initialized but not subscribed |
| ENV | 0x76 | ✓ PASS | ✓ PASS | ? | ✗ FAIL | Initialized but not subscribed |

---

## Symptoms

From MycoBrain Connection Report:
- **AMB (0x77)**: Initialized OK, subscription FAILED
- **ENV (0x76)**: Initialized OK, subscription FAILED

Device status shows:
```
BME688 count: 2 | MycoBrain DeviceManager + BSEC2 | Mycosoft ESP32AB
```

But sensors are not providing data readings.

---

## Root Cause Analysis

### Possible Causes

1. **BSEC2 Configuration Blob Missing or Invalid**
   - BSEC2 requires a configuration blob to be set before subscription
   - If `CFG_PTR` is null or `CFG_LEN` is 0, `setConfig()` is skipped
   - Subscription may fail if config is not properly set

2. **Memory Allocation Issues**
   - BSEC2 requires `BSEC_INSTANCE_SIZE` bytes of memory per sensor
   - If memory allocation fails, subscription will fail
   - Check: `s.bsec.allocateMemory(s.mem)` must succeed

3. **Sample Rate Configuration**
   - BSEC2 requires valid sample rate (BSEC_SAMPLE_RATE_LP or BSEC_SAMPLE_RATE_ULP)
   - Invalid sample rate causes subscription to fail

4. **I2C Communication Issues**
   - Intermittent I2C errors during subscription setup
   - Bus conflicts or timing issues

5. **Firmware Version Mismatch**
   - BSEC2 library version incompatible with firmware
   - Missing required BSEC2 outputs in firmware

---

## Investigation Steps

### Step 1: Check Firmware Serial Output

Connect to COM7 and monitor serial output during boot:

```powershell
# Use any serial monitor (Arduino IDE, PuTTY, etc.)
# Connect to COM7 at 115200 baud
```

Look for these messages:
```
[AMB] begin(0x77)...
[AMB] begin OK
[AMB] setConfig(blob X bytes)...
[AMB] setConfig OK  (or FAILED)
[AMB] updateSubscription(LP, 4 outputs)...
[AMB] updateSubscription OK  (or FAILED)
```

### Step 2: Check BSEC2 Configuration

In firmware code (`MycoBrain_DeviceManager_BSEC2.ino`):

```cpp
if (CFG_PTR && CFG_LEN) {
    Serial.printf("[%s] setConfig(blob %lu bytes)...\n", s.name, (unsigned long)CFG_LEN);
    if (!s.bsec.setConfig(CFG_PTR)) {
        Serial.printf("[%s] setConfig FAILED\n", s.name);
        s.cfgOk = false;
    } else {
        Serial.printf("[%s] setConfig OK\n", s.name);
        s.cfgOk = true;
    }
}
```

**Check:**
- Is `CFG_PTR` defined and non-null?
- Is `CFG_LEN` > 0?
- Does `setConfig()` return true?

### Step 3: Check Memory Allocation

```cpp
s.bsec.allocateMemory(s.mem);
```

**Check:**
- Is `s.mem` array large enough? (`BSEC_INSTANCE_SIZE`)
- Does allocation succeed?
- Are there memory leaks or fragmentation?

### Step 4: Check Sample Rate

```cpp
bsecSensor list[] = {
    BSEC_OUTPUT_IAQ,
    BSEC_OUTPUT_STATIC_IAQ,
    BSEC_OUTPUT_CO2_EQUIVALENT,
    BSEC_OUTPUT_BREATH_VOC_EQUIVALENT
};

if (s.bsec.updateSubscription(list, (uint8_t)ARRAY_LEN(list), s.sampleRate)) {
    // Success
} else {
    // Failure - check BSEC2 status
    Serial.printf("[%s] updateSubscription FAILED (status: %d)\n", s.name, (int)s.bsec.status);
}
```

**Check:**
- What is `s.sampleRate`? (Should be `BSEC_SAMPLE_RATE_LP` or `BSEC_SAMPLE_RATE_ULP`)
- What is the BSEC2 status code after failure?

### Step 5: Check I2C Bus

```cpp
Wire.beginTransmission(s.addr);
if (Wire.endTransmission() != 0) {
    // Sensor not found
}
```

**Check:**
- Can both sensors be detected on I2C scan?
- Are there I2C errors during subscription?
- Is I2C bus speed appropriate? (100kHz recommended)

---

## Diagnostic Commands

### Check Device Status via API

```powershell
# Get device status
curl.exe http://localhost:8003/devices/mycobrain-COM7/status

# Get sensor readings (if subscription worked)
curl.exe http://localhost:8003/devices/mycobrain-COM7/readings
```

### Check Serial Output

```powershell
# Monitor COM7 serial output
# Use Arduino IDE Serial Monitor or:
python -m serial.tools.miniterm COM7 115200
```

### Check Firmware Version

```powershell
# Query device for firmware info
curl.exe http://localhost:8003/devices/mycobrain-COM7/info
```

---

## Solutions

### Solution 1: Verify BSEC2 Configuration Blob

**If config blob is missing:**

1. Download BSEC2 configuration from Bosch Sensortec
2. Include in firmware as byte array
3. Set `CFG_PTR` and `CFG_LEN` appropriately

**Check firmware:**
```cpp
extern const uint8_t bsec_config[];
extern const unsigned int bsec_config_len;

#define CFG_PTR bsec_config
#define CFG_LEN bsec_config_len
```

### Solution 2: Check Memory Allocation

**Ensure sufficient memory:**
```cpp
#include "bsec2.h"

// Per sensor
uint8_t mem_amb[BSEC_INSTANCE_SIZE];
uint8_t mem_env[BSEC_INSTANCE_SIZE];

SensorSlot S_AMB = { "AMB", 0x77, mem_amb };
SensorSlot S_ENV = { "ENV", 0x76, mem_env };
```

### Solution 3: Verify Sample Rate

**Use appropriate sample rate:**
```cpp
// Low Power mode (recommended)
s.sampleRate = BSEC_SAMPLE_RATE_LP;

// Or Ultra Low Power mode
s.sampleRate = BSEC_SAMPLE_RATE_ULP;
```

### Solution 4: Add Error Logging

**Enhance firmware to log BSEC2 status:**
```cpp
if (!s.bsec.updateSubscription(list, (uint8_t)ARRAY_LEN(list), s.sampleRate)) {
    Serial.printf("[%s] updateSubscription FAILED\n", s.name);
    Serial.printf("[%s] BSEC2 Status: %d\n", s.name, (int)s.bsec.status);
    Serial.printf("[%s] BSEC2 Error: %s\n", s.name, s.bsec.getErrorString());
    s.subOk = false;
}
```

### Solution 5: Re-flash Firmware

**If firmware is outdated:**
1. Verify latest firmware version
2. Check for BSEC2 library updates
3. Re-flash device with verified working firmware

---

## Expected Behavior After Fix

Once subscription succeeds, you should see:

1. **Serial Output:**
   ```
   [AMB] updateSubscription OK
   [ENV] updateSubscription OK
   ```

2. **API Response:**
   ```json
   {
     "device_id": "mycobrain-COM7",
     "readings": {
       "amb": {
         "iaq": 25.5,
         "iaqAccuracy": 3,
         "co2eq": 450,
         "voc": 0.5,
         "temperature": 22.3,
         "humidity": 45.2,
         "pressure": 1013.25
       },
       "env": {
         "iaq": 28.1,
         ...
       }
     }
   }
   ```

3. **Real-time Data:**
   - IAQ values updating every few seconds
   - CO2 equivalent values
   - VOC readings
   - Temperature, humidity, pressure

---

## Related Documentation

- `docs/BME688_DUAL_SENSOR_SETUP.md` - Dual sensor configuration
- `docs/BME688_INTEGRATION_COMPLETE_2026-01-09.md` - Integration details
- `firmware/MycoBrain_DeviceManager_BSEC2/` - BSEC2 firmware source
- `docs/MYCOBRAIN_CONNECTION_REPORT_JAN23_2026.md` - Connection setup

---

## Next Actions

1. [ ] Monitor serial output during device boot
2. [ ] Verify BSEC2 configuration blob is present
3. [ ] Check memory allocation for both sensors
4. [ ] Add detailed error logging to firmware
5. [ ] Test with known-good firmware version
6. [ ] Document solution once root cause is identified

---

*Investigation started: January 24, 2026*  
*Status: Awaiting serial output analysis*
