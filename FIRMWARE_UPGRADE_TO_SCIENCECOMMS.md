# MycoBrain Firmware Upgrade to ScienceComms
**Date**: December 31, 2025, 12:50 AM PST  
**Current Firmware**: v3.3.5 (Basic)  
**Target Firmware**: MycoBrain_ScienceComms (Full Features)  
**Repository**: https://github.com/MycosoftLabs/mycobrain/tree/main/firmware/MycoBrain_ScienceComms  

## 🎯 WHY UPGRADE

Current firmware v3.3.5 only supports 71% of UI features.  
ScienceComms firmware will enable ALL advanced features:

- LED Patterns (rainbow, chase, breathe, sparkle)
- Custom buzzer tones with frequency/duration control
- Machine Mode NDJSON protocol
- Optical TX (Camera OOK, Manchester, Spatial Modulation)
- Acoustic TX (sound-based data transmission)
- BLE connectivity
- Full LoRa support
- Mesh networking

## 📋 PRE-UPGRADE CHECKLIST

- [x] Current firmware tested and working
- [x] All services operational
- [x] Device connected on COM5
- [x] Firmware repo cloned
- [ ] Backup current firmware (if possible)
- [ ] Arduino IDE configured
- [ ] Required libraries installed

## 🔧 UPGRADE PROCESS

### Step 1: Verify Repository
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms

# Check firmware files
ls -la
```

### Step 2: Open in Arduino IDE
```
1. Open Arduino IDE
2. File → Open → MycoBrain_ScienceComms.ino
3. Verify board settings match current config
4. Check library dependencies
```

### Step 3: Verify Arduino Settings
**From Working Config**:
- Board: ESP32-S3 Dev Module
- USB CDC: Enabled
- USB DFU: Enabled  
- PSRAM: OPI PSRAM
- CPU Frequency: 240 MHz
- Flash Size: 16MB
- Partition: 16MB flash (3MB app / 9.9MB FATFS)
- Upload Speed: 921600
- Upload Port: COM5

### Step 4: Compile and Upload
```
1. Sketch → Verify/Compile
2. Wait for compilation
3. Sketch → Upload
4. Monitor serial output
```

### Step 5: Test New Features
After upload, test ALL previously unavailable features:
- LED patterns
- Custom tones
- Optical TX
- Acoustic TX
- BLE
- LoRa
- Mesh

## ⚠️ EXPECTED CHANGES

### What Will Change
- More commands available
- Advanced protocols enabled
- New capabilities unlocked
- Possibly different command syntax

### What Should Stay Same
- COM port (COM5)
- Baud rate (115200)
- Basic LED/buzzer controls
- Sensor readings
- MDP protocol compatibility

## 🧪 POST-UPGRADE TESTING PLAN

Run the comprehensive test suite again:
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
powershell -ExecutionPolicy Bypass -File scripts\test_mycobrain_features.ps1
```

Expected results after upgrade:
- LED Patterns: 6/6 → **Should all work** ✅
- Custom Tones: 4/5 → **Should be 5/5** ✅
- Optical TX: 3/3 → **Should all work** ✅
- Acoustic TX: 0/3 → **Should be 3/3** ✅
- BLE: 0/1 → **Should be 1/1** ✅
- Mesh: 0/1 → **Should be 1/1** ✅
- LoRa: 1/2 → **Should be 2/2** ✅

**Target Success Rate**: 100% (28/28 features)

## 📊 CURRENT vs POST-UPGRADE

| Feature Category | Current (v3.3.5) | After ScienceComms | Improvement |
|------------------|------------------|-------------------|-------------|
| LED Patterns | ❌ 0/6 | ✅ 6/6 | +600% |
| Custom Tones | ⚠️ 4/5 | ✅ 5/5 | +20% |
| Optical TX | ❌ 0/3 | ✅ 3/3 | +300% |
| Acoustic TX | ❌ 0/3 | ✅ 3/3 | +300% |
| BLE | ❌ 0/1 | ✅ 1/1 | +100% |
| Mesh | ❌ 0/1 | ✅ 1/1 | +100% |
| LoRa | ⚠️ 1/2 | ✅ 2/2 | +100% |
| **TOTAL** | **20/28 (71%)** | **28/28 (100%)** | **+40%** |

## 🚀 BENEFITS OF UPGRADE

### For Development
- Full UI feature parity
- No confusion about missing features
- Complete testing capability
- Advanced communication protocols

### For Science
- Optical data transmission experiments
- Acoustic modem research
- Wireless sensor networks
- Multi-device coordination

### For Users
- All UI buttons functional
- Full feature set available
- Better user experience
- Future-proof system

## ⚡ QUICK START

```powershell
# 1. Navigate to firmware
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms

# 2. Open in Arduino IDE
start MycoBrain_ScienceComms.ino

# 3. Verify settings match working config
# 4. Upload to COM5
# 5. Test all features
# 6. Enjoy 100% functionality!
```

---
**Status**: Firmware repository identified  
**Action**: Clone → Compile → Upload → Test  
**ETA**: 30 minutes  
**Expected Outcome**: 100% feature support  


