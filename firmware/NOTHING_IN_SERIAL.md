# Nothing in Serial Monitor - Troubleshooting

## Problem
Changed USB cable, now nothing appears in Serial Monitor.

## Possible Causes

### 1. Wrong COM Port
**The COM port number may have changed!**

When you change USB cable/port, Windows assigns a NEW COM port number.

**Check:**
- Tools → Port → Look for NEW port (might be COM7, COM8, etc.)
- Try ALL available COM ports

### 2. Charge-Only Cable
**New cable might be charge-only (not data-capable)**

Charge-only cables can't transfer data, only power.

**Check:**
- Does the cable work for data on other devices?
- Try the OLD cable again
- Use a known data-capable cable

### 3. Board Not Getting Power
**Board might not be powered on**

**Check:**
- Is there an LED on the board? Does it light up?
- Try pressing RESET button on ESP32
- Unplug/replug USB cable

### 4. Board Completely Dead
**Board might be damaged**

**Check:**
- Try old cable again - does it work?
- Try different USB port
- Check for physical damage

## Steps to Diagnose

### Step 1: Check COM Ports
1. **Unplug ESP32**
2. **Tools → Port** - note which ports are available
3. **Plug in ESP32**
4. **Tools → Port** - see which NEW port appeared
5. **Select that port**

### Step 2: Try Old Cable
1. **Unplug new cable**
2. **Plug in old cable**
3. **Check if Serial Monitor shows anything**
4. **If old cable works, new cable is charge-only**

### Step 3: Check Power
1. **Look for LED on board** - does it light up?
2. **Press RESET button** - does anything happen?
3. **Try different USB port**

### Step 4: Upload Test
1. **Try uploading** - does it succeed?
2. **If upload fails, board might not be connected**
3. **If upload succeeds but no Serial output, baud rate might be wrong**

## Quick Test

1. **Unplug ESP32**
2. **Wait 5 seconds**
3. **Plug back in**
4. **Check Device Manager** (Win+X → Device Manager → Ports)
5. **See if COM port appears**
6. **Note the COM number**
7. **Select that port in Arduino IDE**

## Report Back

Please tell me:
1. **What COM ports do you see in Arduino IDE?**
2. **Does the board have an LED? Does it light up?**
3. **Can you upload code?** (even if Serial doesn't work)
4. **Does old cable work?**

