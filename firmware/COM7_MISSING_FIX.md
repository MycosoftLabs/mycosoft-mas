# COM7 Missing - Side-B Not Recognized

## Problem
- Both USBs plugged in
- COM7 disappeared
- Only see COM4 (ESP32) and COM1, COM2, COM3

## Possible Causes

### 1. Side-B USB Cable Issue
**Most likely**: The USB cable for Side-B is **charge-only** (not data-capable)

**Test**:
- **Unplug Side-B USB**
- **Try a different USB cable** (known data-capable cable)
- **Plug back in**
- **Check if COM port appears**

### 2. Side-B Not Powered
**Check**:
- **Is Side-B LED on?** (should have power indicator)
- **Try different USB port** on computer
- **Try USB 2.0 port** (more reliable than USB 3.0)

### 3. Driver Issue
**Check Device Manager**:
1. **Win+X → Device Manager**
2. **Look under "Ports (COM & LPT)"**
3. **Look for yellow triangle** or "Unknown device"
4. **If found**: Right-click → Update driver

### 4. Side-B Hardware Issue
**Check**:
- **Does Side-B have power LED?** (is it lit?)
- **Try unplugging/replugging** Side-B USB
- **Try different USB port** on computer

## Solutions

### Solution 1: Try Different USB Cable
1. **Unplug Side-B USB**
2. **Use the cable that works for Side-A** (COM4)
3. **Plug into Side-B**
4. **Check if COM port appears**

### Solution 2: Try Different USB Port
1. **Unplug Side-B USB**
2. **Try different USB port** on computer
3. **Prefer USB 2.0 ports**
4. **Wait 10 seconds**
5. **Check COM ports**

### Solution 3: Check Device Manager
1. **Win+X → Device Manager**
2. **Expand "Ports (COM & LPT)"**
3. **Unplug Side-B USB** - see what disappears
4. **Plug Side-B USB back in** - see what appears
5. **Note the COM number** (might be different than COM7)

### Solution 4: Test Side-B Hardware
1. **Unplug Side-B USB**
2. **Plug Side-B USB into different computer** (if available)
3. **See if it's recognized there**
4. **If not recognized anywhere**: Hardware issue

## Quick Test

**Try this**:
1. **Unplug Side-B USB**
2. **Wait 5 seconds**
3. **Plug Side-B USB into the SAME port as Side-A** (where COM4 works)
4. **Check if new COM port appears**
5. **If yes**: Cable or port issue
6. **If no**: Hardware issue

## Alternative: Upload to Side-B Later

**You can test Side-A alone first**:
- Side-A works on COM4 ✅
- Test all Side-A features
- Upload Side-B later when cable/port issue is resolved

## Report Back

Please tell me:
1. **Does Side-B have a power LED? Is it on?**
2. **Did you try a different USB cable?**
3. **Did you try a different USB port?**
4. **What does Device Manager show?** (any errors?)

