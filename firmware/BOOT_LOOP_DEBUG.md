# Boot Loop Debugging Guide

## Still Resetting? Let's Debug

### Step 1: Test with Minimal Code

Upload `MycoBrain_SideA_MINIMAL.ino` to test if hardware is OK:

1. **Open** `firmware/MycoBrain_SideA/MycoBrain_SideA_MINIMAL.ino`
2. **Upload** to COM6
3. **Open Serial Monitor** (115200 baud)

**Expected:**
- Should see "Loop running: X seconds" every second
- Should NOT reset

**If minimal code works:**
- Hardware is OK
- Issue is in sensor/BSEC code

**If minimal code also resets:**
- Hardware issue (power, connections, etc.)

### Step 2: Check Serial Monitor Output

With the main firmware, what's the LAST message you see before reset?

Common crash points:
- "Initializing sensors..." → Crash in `initSensors()`
- "Trying AMB sensor..." → Crash in `slotInit()`
- "BSEC begin() failed..." → BSEC library issue
- Nothing at all → Crash very early in setup()

### Step 3: Disable Sensors Temporarily

If minimal code works, try disabling sensors:

In `MycoBrain_SideA.ino`, comment out:
```cpp
// bool sensorsOk = initSensors();  // Disable this line
bool sensorsOk = false;  // Force no sensors
```

If it stops resetting, the issue is in sensor initialization.

### Step 4: Check Power

- **Try different USB cable** (data-capable, not charge-only)
- **Try different USB port** (USB 2.0 preferred)
- **Avoid USB hubs** - connect directly
- **Check if USB port provides enough power**

### Step 5: Check for Exceptions

The updated code now has try-catch blocks. Look for:
- "ERROR: Exception during sensor init!"
- "ERROR: BSEC AMB run() failed"
- "ERROR: sendTelemetry() failed"

These will tell you exactly where it's crashing.

## Most Likely Causes

1. **BSEC library crash** - Memory allocation or initialization failing
2. **I2C bus issue** - Sensors not responding, causing hang
3. **Power issue** - Not enough power, causing brownout reset
4. **Watchdog reset** - Code taking too long, watchdog kills it

## Quick Test

**Upload minimal code first** - this will tell us if it's hardware or software!

