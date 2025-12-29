# Testing Instructions

## Current Status
The main `MycoBrain_SideA.ino` file now contains the **minimal test code**.

## Test Steps

### 1. Upload the Minimal Code
- The file `MycoBrain_SideA.ino` already has minimal test code
- **Upload it to COM6**
- **Open Serial Monitor** (115200 baud)

### 2. What to Look For

**If it works (no resetting):**
- You'll see: "Loop running: X seconds" every second
- Hardware is OK ✅
- Issue is in sensor/BSEC code

**If it still resets:**
- Hardware issue (power, USB, connections)
- Try different USB cable/port

### 3. Next Steps Based on Results

**If minimal code works:**
- I'll restore the full firmware with sensors disabled first
- Then we'll enable sensors one at a time

**If minimal code also resets:**
- Check USB cable (use data-capable cable)
- Try different USB port
- Check for loose connections
- May be hardware fault

## Report Back

Please tell me:
1. **Does the minimal code work?** (no resetting)
2. **What do you see in Serial Monitor?**

Then I can help fix the full firmware!

