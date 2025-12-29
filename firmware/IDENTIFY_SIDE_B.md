# Identify Side-B Port

## Current Ports
- **COM1, COM2**: Motherboard serial ports
- **COM3**: USB Serial Device (VID:PID=046B:FFB0) - **Might be Side-B?**
- **COM4**: ESP32-S3 (VID:PID=303A:1001) - **This is Side-A** ✅

## Test if COM3 is Side-B

### Method 1: Unplug Test
1. **Unplug Side-B USB**
2. **Check COM ports** - does COM3 disappear?
3. **If yes**: COM3 is Side-B
4. **If no**: Side-B not recognized

### Method 2: Try Uploading to COM3
1. **Open**: `firmware/MycoBrain_SideB/MycoBrain_SideB.ino`
2. **Select COM3** in Arduino IDE
3. **Try uploading**
4. **If it works**: COM3 is Side-B!

### Method 3: Check Device Manager
1. **Win+X → Device Manager**
2. **Expand "Ports (COM & LPT)"**
3. **Unplug Side-B USB** - see what disappears
4. **Plug back in** - see what appears
5. **Note the COM number**

## If Side-B Not Recognized

### Possible Issues:
1. **USB cable is charge-only** (can't transfer data)
2. **Side-B not powered** (no LED?)
3. **Driver missing** (check Device Manager)
4. **Hardware issue** (Side-B board problem)

### Solutions:
1. **Try different USB cable** (use the one that works for Side-A)
2. **Try different USB port** on computer
3. **Check if Side-B has power LED** - is it on?
4. **Check Device Manager** for errors

## Alternative: Test Side-A Alone First

**You can proceed with Side-A testing**:
- Side-A works on COM4 ✅
- Test all Side-A features (buzzer, NeoPixel, sensors)
- Upload Side-B later when cable/port issue is resolved
- Side-A can work standalone (doesn't need Side-B for basic testing)

## Quick Test

**Try uploading Side-B to COM3**:
1. Make sure Serial Monitor is closed
2. Select COM3
3. Upload Side-B firmware
4. If it works, COM3 is Side-B!

**Or test which port is Side-B**:
1. Unplug Side-B USB
2. Check which COM port disappears
3. That's Side-B's port


