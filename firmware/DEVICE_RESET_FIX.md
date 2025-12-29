# Device Reset Fix - No Serial Output

## Problem
- No output in Serial Monitor
- Device disconnects when hitting RESET
- Upload failing

## This Means
The device might be in a bad state or firmware crashed.

## Solution: Force Boot Mode

### Step 1: Put Device in Boot Mode
1. **Unplug USB cable** from Side-A
2. **Wait 5 seconds**
3. **Hold BOOT button** (keep holding)
4. **Plug USB cable back in** (while holding BOOT)
5. **Keep holding BOOT** for 3 seconds
6. **Release BOOT**

### Step 2: Upload Immediately
1. **Arduino IDE should show "Connecting..."**
2. **If not, click Upload** immediately
3. **Should work now**

## Alternative: Lower Upload Speed

1. **Tools → Upload Speed → 115200**
2. **Use BOOT button method above**
3. **Try upload**

## If Still Fails

### Check Board Settings
1. **Tools → Board → ESP32S3 Dev Module**
2. **Tools → CPU Frequency → 240MHz**
3. **Tools → Flash Frequency → 80MHz**
4. **Tools → Flash Mode → QIO**
5. **Tools → Flash Size → 4MB (32Mb)**
6. **Tools → Partition Scheme → Default 4MB with spiffs**
7. **Tools → USB CDC On Boot → Enabled**

### Try Different USB Port
1. **Unplug from current port**
2. **Try different USB port** (USB 2.0 preferred)
3. **Try upload**

## Emergency: Erase Flash

If nothing works, try erasing flash first:

1. **Tools → Erase All Flash Before Sketch Upload → Enabled**
2. **Use BOOT button method**
3. **Upload**

This will completely erase and reinstall firmware.

## Quick Steps

1. ✅ **Unplug USB**
2. ✅ **Hold BOOT button**
3. ✅ **Plug USB back in** (keep holding BOOT)
4. ✅ **Hold BOOT for 3 seconds**
5. ✅ **Release BOOT**
6. ✅ **Click Upload immediately**

Try the force boot mode method - unplug, hold BOOT, plug back in!


