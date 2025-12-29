# COM4 Upload Fix - No Serial Data Received

## Problem
"Failed to connect to ESP32-S3: No serial data received"

## Solution: Use BOOT Button Method

### Step 1: Close Serial Monitor
1. **Close Serial Monitor** (if open)
2. **Wait 2 seconds**

### Step 2: Put ESP32 in Boot Mode
1. **Hold BOOT button** on Side-A ESP32
2. **Press and release RESET button** (while holding BOOT)
3. **Keep holding BOOT**

### Step 3: Upload
1. **Click Upload** in Arduino IDE
2. **Keep holding BOOT** until you see "Connecting..."
3. **Release BOOT** when upload starts
4. **Wait for upload to complete**

## Alternative: Lower Upload Speed

If BOOT button doesn't work:

1. **Tools → Upload Speed → 115200** (instead of 921600)
2. **Try upload again**
3. **Still use BOOT button method**

## If Still Fails

### Check Serial Monitor
- **Make sure Serial Monitor is closed**
- **Close ALL Arduino IDE windows**
- **Restart Arduino IDE**
- **Try again**

### Check USB Connection
- **Unplug USB cable**
- **Wait 5 seconds**
- **Plug back in**
- **Wait 10 seconds**
- **Try upload again**

### Try Different USB Port
- **Unplug from current port**
- **Try different USB port** (USB 2.0 preferred)
- **Try upload again**

## Quick Steps

1. ✅ **Close Serial Monitor**
2. ✅ **Hold BOOT button**
3. ✅ **Press RESET button** (release, keep holding BOOT)
4. ✅ **Click Upload**
5. ✅ **Release BOOT when "Connecting..." appears**

Try the BOOT button method - that should fix it!

