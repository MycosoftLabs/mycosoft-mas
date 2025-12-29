# Hardware Reset Issue - Minimal Code Still Resetting

## Problem
Even minimal code (just Serial.println) is causing continuous resets.

## This Indicates Hardware Issue

Since minimal code has no sensors, no BSEC, no complex code - if it resets, it's hardware.

## Possible Causes

### 1. Power Supply Issue (Most Likely)
- **USB port not providing enough power**
- **USB cable is charge-only (not data-capable)**
- **USB hub not providing enough power**
- **Brownout detector triggering**

### 2. USB Connection Issue
- **Loose USB connection**
- **Bad USB cable**
- **USB port damaged**

### 3. Hardware Fault
- **Short circuit on board**
- **Damaged ESP32**
- **Power regulator issue**

## Solutions to Try

### Solution 1: Different USB Cable
1. **Use a different USB cable**
2. **Make sure it's DATA-CAPABLE** (not charge-only)
3. **Try shorter cable** (longer cables can have voltage drop)
4. **Try USB 2.0 cable** (not USB 3.0)

### Solution 2: Different USB Port
1. **Try different USB port on computer**
2. **Prefer USB 2.0 ports** (more stable power)
3. **Avoid USB hubs** - connect directly
4. **Try front panel USB** (if desktop)
5. **Try rear panel USB** (if desktop)

### Solution 3: Check Serial Monitor Output
**What do you see before it resets?**

- **Nothing at all?** → Power issue, board not getting power
- **Partial messages?** → Brownout (power drops, resets)
- **Garbage characters?** → Baud rate wrong or power issue
- **Same message repeating?** → Continuous reset loop

### Solution 4: Disable Brownout Detector
Add this to setup() to disable brownout detection:

```cpp
void setup() {
  // Disable brownout detector
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(115200);
  delay(2000);
  // ... rest of code
}
```

**WARNING:** This disables protection - only use for testing!

### Solution 5: Check Hardware
1. **Inspect board for:**
   - Loose connections
   - Short circuits
   - Burn marks
   - Damaged components

2. **Check USB connector:**
   - Is it loose?
   - Are pins bent?
   - Is it making good contact?

### Solution 6: External Power
If board has external power option:
- **Use external 5V power supply**
- **USB can just be for data**

## What to Report

Please tell me:
1. **What do you see in Serial Monitor?** (before reset)
2. **How often does it reset?** (every second? every few seconds?)
3. **Have you tried different USB cable/port?**
4. **Does the board LED blink?** (if it has one)

## Quick Test

Try this even simpler code to see if ANY code works:

```cpp
void setup() {
  Serial.begin(115200);
  delay(3000);  // Longer delay
  Serial.println("TEST");
}

void loop() {
  delay(1000);
  Serial.println("ALIVE");
}
```

If even this resets, it's definitely hardware/power.

