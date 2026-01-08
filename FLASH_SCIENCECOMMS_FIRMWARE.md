# Flash MycoBrain ScienceComms Firmware
**Repository**: https://github.com/MycosoftLabs/mycobrain/tree/main/firmware/MycoBrain_ScienceComms  
**Current**: v3.3.5 (Basic - 71% features)  
**Target**: ScienceComms (Full - 100% features)  
**Device**: ESP32-S3 on COM5  

## 🎯 OBJECTIVE

Flash the ScienceComms firmware to enable ALL advanced features currently shown in the Device Manager UI.

## 📋 PRE-FLASH CHECKLIST

- [x] Device tested with current firmware (works)
- [x] COM5 connection stable
- [x] Arduino IDE settings documented
- [x] Current capabilities documented
- [x] Firmware repo cloned locally
- [ ] Libraries installed
- [ ] Compile successful
- [ ] Upload successful
- [ ] New features tested

## 🔧 FLASH PROCEDURE

### Step 1: Open Firmware in Arduino IDE
```
1. Launch Arduino IDE
2. File → Open
3. Navigate to: C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms
4. Open the .ino file
```

### Step 2: Configure Board Settings
**Use EXACT settings from working config**:
```
Board: ESP32-S3 Dev Module
USB CDC on Boot: Enabled
USB DFU on Boot: Enabled
USB Firmware MSC on Boot: Disabled
USB Mode: Hardware CDC and JTAG
JTAG Adapter: Integrated USB JTAG
PSRAM: OPI PSRAM
CPU Frequency: 240 MHz
Flash Mode: QIO 80MHz
Flash Size: 16MB (128Mb)
Partition Scheme: 16M Flash (3MB APP / 9.9MB FATFS)
Upload Speed: 921600
Upload Port: COM5
Erase Flash: Disabled (preserve data)
```

### Step 3: Install Required Libraries
Check firmware code for library dependencies (likely includes):
- FastLED (for LED patterns)
- WiFi.h (ESP32 built-in)
- BLE (ESP32 built-in)
- LoRa library (if using)
- ESP-NOW or Painless Mesh
- BME68x sensor library

**Install via Arduino IDE**:
1. Tools → Manage Libraries
2. Search and install each required library
3. Use latest stable versions

### Step 4: Compile Firmware
```
1. Sketch → Verify/Compile
2. Wait for compilation (may take 2-3 minutes)
3. Check for errors
4. Fix any library or dependency issues
5. Verify compilation success
```

### Step 5: Disconnect MycoBrain Service
**IMPORTANT**: Stop the MycoBrain service before flashing
```powershell
# Find and kill the service
$proc = Get-Process python | Where-Object {$_.Path -like "*mycobrain*"}
if ($proc) {
    $proc | Stop-Process -Force
    Write-Host "MycoBrain service stopped"
}

# Or restart computer to ensure clean state
```

### Step 6: Upload Firmware
```
1. Ensure COM5 is selected
2. Sketch → Upload
3. Monitor upload progress
4. Wait for "Hard resetting via RTS pin..."
5. Verify upload complete
```

### Step 7: Verify New Firmware
**Open Serial Monitor** (115200 baud):
```
1. Tools → Serial Monitor
2. Set baud rate: 115200
3. Type: help
4. Verify new commands appear:
   - machine init
   - optical tx
   - acoustic tx
   - ble start
   - mesh join
   - lora send
   - led pattern
   - buzzer freq
```

### Step 8: Restart MycoBrain Service
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\services\mycobrain
python mycobrain_service_standalone.py
```

### Step 9: Test in Browser
1. Navigate to http://localhost:3000/natureos/devices
2. Verify device reconnects
3. Test all advanced features:
   - Click "Initialize Machine Mode"
   - Test LED patterns (rainbow, chase, etc.)
   - Test custom tones (frequency slider)
   - Test Optical TX profiles
   - Test Acoustic TX
   - Test Comms tab (LoRa, BLE, Mesh)

### Step 10: Run Automated Tests
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
powershell -ExecutionPolicy Bypass -File scripts\test_mycobrain_features.ps1
```

**Expected**: 28/28 tests pass (100%)

## ⚠️ TROUBLESHOOTING

### Issue: Compilation Errors
**Solution**: Install missing libraries via Library Manager

### Issue: Upload Fails
**Solution**: 
- Verify COM5 is correct port
- Try pressing BOOT button during upload
- Check USB cable connection
- Restart Arduino IDE

### Issue: Device Won't Connect After Flash
**Solution**:
- Check baud rate (115200)
- Power cycle device
- Verify firmware uploaded successfully
- Check serial monitor for boot messages

### Issue: New Features Don't Work
**Solution**:
- Verify firmware version with `status` command
- Check that libraries compiled in
- Review serial output for error messages
- Ensure hardware modules present (LoRa, etc.)

## 🎯 SUCCESS CRITERIA

After successful flash:
- ✅ Device boots and shows new version
- ✅ `help` command shows extended command list
- ✅ Machine Mode initializes
- ✅ LED patterns work (rainbow visible)
- ✅ Custom tones play at any frequency
- ✅ Optical TX LED flashes visible
- ✅ Acoustic TX sounds audible
- ✅ BLE advertises and connects
- ✅ All 28 features test successfully

## 📊 EXPECTED TIMELINE

| Step | Time | Cumulative |
|------|------|------------|
| Open in Arduino IDE | 2 min | 2 min |
| Configure board settings | 3 min | 5 min |
| Install libraries | 5 min | 10 min |
| Compile firmware | 3 min | 13 min |
| Stop service | 1 min | 14 min |
| Upload firmware | 2 min | 16 min |
| Verify + test | 5 min | 21 min |
| Restart service | 1 min | 22 min |
| Browser testing | 5 min | 27 min |
| Automated tests | 3 min | 30 min |
| **TOTAL** | **~30 minutes** | - |

## 🔄 ROLLBACK PLAN

If new firmware has issues:
1. Re-flash v3.3.5 (if you have the .bin file)
2. OR compile previous working firmware
3. OR use stable release from GitHub
4. Service will work with any firmware version

## 📝 NEXT ACTIONS

**Ready to flash?**

1. **Now**: Open Arduino IDE with ScienceComms firmware
2. **Verify**: Check library dependencies
3. **Upload**: Flash to COM5
4. **Test**: Run all 28 feature tests
5. **Celebrate**: 100% functionality! 🎉

---
**Status**: Ready to upgrade  
**Risk**: Low (can rollback)  
**Reward**: High (40% more features)  
**Recommendation**: PROCEED WITH FLASH  


