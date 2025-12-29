# Step-by-Step Upload Guide

## ⚠️ CRITICAL: Boot Mode is Required

ESP32-S3 **MUST** be manually put into boot mode before every upload.
There is NO software workaround - this is a hardware requirement.

## Complete Procedure

### Step 1: Prepare Arduino IDE
1. Open `firmware/MycoBrain_SideA/MycoBrain_SideA.ino`
2. **Tools → Board**: `ESP32-S3 Dev Module`
3. **Tools → Port**: `COM4`
4. **Tools → Upload Speed**: `115200` (or `9600` if fails)
5. **Tools → Erase All Flash Before Sketch Upload**: ✅ **ENABLED**
6. **Close Serial Monitor** (if open)

### Step 2: Put Device in Boot Mode
**Follow these steps EXACTLY:**

1. **UNPLUG** USB cable from Side-A board
   - Wait 30 seconds (let capacitors discharge)

2. **HOLD** the BOOT button on the board
   - Keep holding it

3. **PLUG** USB cable back into Side-A
   - Still holding BOOT button

4. **HOLD BOOT** for 5 full seconds
   - Count: "one thousand one, one thousand two..." to five

5. **RELEASE** BOOT button
   - Let go completely

6. **WAIT** 2 seconds
   - Don't touch anything

### Step 3: Upload Immediately
1. **Click Upload** button in Arduino IDE
   - Do this within 5 seconds of releasing BOOT
   - If you wait too long, device exits boot mode

2. **Watch for**:
   - "Connecting..." should change to "Writing at 0x..."
   - Progress bar appears
   - "Done uploading" message

### Step 4: Verify
1. **Open Serial Monitor** (115200 baud)
2. **Press RESET** button on board
3. **Should see**: SuperMorgIO POST screen and boot jingle

## If Upload Fails

### "Connecting......................................" (forever)
- **Boot mode failed** - repeat Step 2 more carefully
- Try holding BOOT longer (10 seconds)
- Try different USB cable
- Try different USB port (USB 2.0 preferred)

### "Port COM4 is busy"
- Close Serial Monitor
- Close any other programs using COM4
- Restart Arduino IDE

### "Failed to connect: No serial data received"
- Device not in boot mode
- Follow Step 2 again
- Try lower upload speed (9600)

## Alternative Boot Mode Method

If the above doesn't work:

1. **Hold BOOT** button
2. **Press and release RESET** button (while holding BOOT)
3. **Keep holding BOOT** for 3 seconds
4. **Release BOOT**
5. **Upload immediately**

## Why This is Necessary

- ESP32-S3 has two modes: **Normal** (running firmware) and **Bootloader** (accepting uploads)
- Boot mode is triggered by **BOOT button** or **DTR/RTS** signals
- If firmware is running, it won't enter boot mode automatically
- USB CDC on ESP32-S3 requires manual boot mode entry

## Success Checklist

- [ ] USB cable unplugged for 30 seconds
- [ ] BOOT button held while plugging USB in
- [ ] BOOT held for full 5 seconds
- [ ] BOOT released, waited 2 seconds
- [ ] Upload clicked within 5 seconds
- [ ] "Writing at 0x..." appears (not just "Connecting...")
- [ ] "Done uploading" message appears

## Next Steps After Upload

1. Open Serial Monitor (115200 baud)
2. Press RESET on board
3. Type `help` to see commands
4. Type `status` to check sensors
5. Type `led rgb 0 255 0` to test LED (green)


