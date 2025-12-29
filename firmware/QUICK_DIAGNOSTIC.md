# Quick Diagnostic - Nothing in Serial

## Current Status
- Changed USB cable
- Nothing appears in Serial Monitor
- COM3 and COM6 are available

## Step-by-Step Diagnosis

### Step 1: Check Which Port
1. **Unplug ESP32**
2. **Tools → Port** - note available ports
3. **Plug ESP32 back in**
4. **Tools → Port** - see which NEW port appeared
5. **Select that port** (might be COM3 or COM6)

### Step 2: Try Both Ports
Since both COM3 and COM6 are USB Serial:
- **Try COM3 first**
- **Open Serial Monitor** (115200 baud)
- **Wait 10 seconds**
- **If nothing, try COM6**

### Step 3: Check Upload
1. **Try uploading code** to COM6
2. **Does upload succeed?**
   - **If YES** → Port is correct, issue is Serial output
   - **If NO** → Try COM3

### Step 4: Check Cable
**New cable might be charge-only:**
- **Try old cable again**
- **Does Serial Monitor show anything with old cable?**
- **If old cable works, new cable is charge-only**

### Step 5: Check Power
**Is board getting power?**
- **Look for LED on board** - does it light up?
- **Press RESET button** - does anything happen?
- **Try different USB port on computer**

### Step 6: Try Different Baud Rates
In Serial Monitor, try:
- **115200** (standard)
- **9600** (slower, more reliable)
- **230400** (faster)

## Most Likely Issues

1. **Wrong COM port** → Try COM3 instead of COM6
2. **Charge-only cable** → New cable can't transfer data
3. **Board resetting too fast** → Can't see output before reset

## Quick Test

**Try this:**
1. **Select COM3** in Arduino IDE
2. **Open Serial Monitor** (115200)
3. **Press RESET button on ESP32**
4. **Watch for output**

**Then try:**
1. **Select COM6** in Arduino IDE
2. **Repeat above**

## Report Back

Please tell me:
1. **Which port did you try?** (COM3 or COM6)
2. **Can you upload code?** (does upload succeed?)
3. **Does old cable work?**
4. **Is there an LED on board? Does it light up?**

