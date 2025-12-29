# Both USBs Needed for Full System

## ✅ Current Status
- **Side-A**: COM4 ✅ Uploaded and working
- **Side-B**: COM7 ⚠️ Upload issue

## 🔌 USB Setup

### YES - Plug in BOTH USBs!
You need **both USB cables plugged in** for:
1. **Side-A** (COM4) - Sensor MCU
2. **Side-B** (COM7) - Router MCU

They communicate with each other via UART, but each needs USB for:
- **Power**
- **Serial communication with PC**
- **Firmware upload**

## 🔧 Fix COM7 Upload Issue

### Step 1: Close Serial Monitor
1. **Close ALL Serial Monitor windows** in Arduino IDE
2. **Close any other programs** using COM7
3. **Wait 5 seconds**

### Step 2: Check COM7
1. **Unplug Side-B USB**
2. **Check COM ports** - COM7 should disappear
3. **Plug Side-B USB back in**
4. **Check COM ports** - COM7 should reappear
5. **Wait 10 seconds** for Windows to recognize it

### Step 3: Try Upload Again
1. **Make sure Serial Monitor is closed**
2. **Select COM7** in Arduino IDE
3. **Click Upload**

### Step 4: If Still Fails
Try **BOOT button method**:
1. **Hold BOOT button** on Side-B ESP32
2. **Click Upload** in Arduino IDE
3. **Keep holding BOOT** until you see "Connecting..."
4. **Release BOOT** when upload starts

## 📋 Upload Order

### Option 1: Upload One at a Time (Recommended)
1. **Upload Side-A** to COM4 ✅ (DONE)
2. **Close Serial Monitor** for Side-A
3. **Upload Side-B** to COM7
4. **Then plug in both USBs** and test

### Option 2: Both Plugged In
1. **Plug in both USBs**
2. **Upload Side-A** to COM4 ✅ (DONE)
3. **Close Serial Monitor** for Side-A
4. **Upload Side-B** to COM7
5. **Test both together**

## 🎯 After Both Uploaded

### Test Setup
1. **Both USBs plugged in**
2. **Side-A on COM4** (sensors, telemetry)
3. **Side-B on COM7** (router, forwarding)

### Test Communication
1. **Open Serial Monitor for Side-B** (COM7, 115200)
2. **Should see**: "Side-A connected"
3. **Send command to Side-B**:
   ```json
   {"cmd":"ping"}
   ```
4. **Should forward to Side-A** and get response

## ⚠️ Important Notes

- **Don't open Serial Monitor** on the port you're uploading to
- **Close Serial Monitor** before uploading
- **Both devices need power** (both USBs)
- **Side-A and Side-B communicate via UART** (not USB)

## 🔍 Troubleshooting COM7

If COM7 still won't work:
1. **Try different USB port** on computer
2. **Try different USB cable** for Side-B
3. **Check Device Manager** - does COM7 show errors?
4. **Restart Arduino IDE**
5. **Try BOOT button method**

Try uploading Side-B to COM7 again after closing Serial Monitor!

