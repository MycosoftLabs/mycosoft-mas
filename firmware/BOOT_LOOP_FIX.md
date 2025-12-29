# Boot Loop Fix - "ESP-ROM:esp32s3-20210327" and Resetting

## Problem
Device shows bootloader message then resets continuously. This is a **boot loop** caused by firmware crashing.

## Fix Applied
I've updated the firmware with:

1. **Brownout Detector Disabled** - Prevents resets during sensor initialization
2. **Watchdog Feeding** - Added `yield()` calls to prevent watchdog timeouts
3. **Error Handling** - Only run sensors if they're properly initialized
4. **Delays** - Added small delays to prevent timing issues

## Upload the Fixed Firmware

1. **Open** `firmware/MycoBrain_SideA/MycoBrain_SideA.ino` in Arduino IDE
2. **Put device in boot mode** (unplug, hold BOOT, plug in, hold 5 sec, release)
3. **Upload** the fixed firmware
4. **Open Serial Monitor** (COM7, 115200)
5. **Press RESET** - should see output without crashing

## If Still Crashing

### Option 1: Check Hardware
- Verify BME688 sensors are connected correctly
- Check I2C connections (SDA=5, SCL=4)
- Verify power supply is stable

### Option 2: Minimal Test
If sensors are causing the crash, we can create a minimal version that:
- Doesn't initialize sensors
- Just prints "Hello World"
- Tests if hardware is OK

### Option 3: Check Libraries
- Make sure BSEC2 library version matches Garrett's
- Check if libraries are compatible with your ESP32-S3 board

## What Changed

```cpp
// Added at top
#include "soc/rtc_cntl_reg.h"

// Added in setup()
WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout

// Added in loop()
yield(); // Feed watchdog
delay(10); // Prevent timing issues

// Added in slotInit()
yield(); // Feed watchdog during sensor init
```

## Expected Behavior After Fix

- Device boots without resetting
- Serial output appears
- Sensors initialize (or fail gracefully)
- No continuous rebooting
