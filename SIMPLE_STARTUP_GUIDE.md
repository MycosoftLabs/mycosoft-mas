# SIMPLE System Startup After Restart

## ✅ WHAT WE ACCOMPLISHED (Pushed to GitHub):
1. Fixed website bug ✅
2. Enhanced MINDEX ✅  
3. Flashed Side-A with ScienceComms firmware ✅
4. Tested 28 features ✅
5. All code saved ✅

## 🚀 AFTER YOU RESTART PC:

### Step 1: Start Services (2 minutes)
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

# Start Docker containers
docker-compose -f docker-compose.always-on.yml up -d mycosoft-website mindex

# Start MycoBrain service (port will be free after restart)
cd services\mycobrain
python mycobrain_service_standalone.py
```

### Step 2: Open Browser (1 minute)

**Main URLs:**
- **CREP Dashboard**: http://localhost:3000/dashboard/crep
- **Device Manager**: http://localhost:3000/natureos/devices
- **NatureOS**: http://localhost:3000/natureos

### Step 3: Connect Device in UI
- Click "COM5" button
- Device appears with ScienceComms firmware
- Test all features!

## 🧪 FEATURES TO TEST (All Should Work Now):

### In Browser UI:
1. **Controls Tab**:
   - ✅ LED presets (Red, Green, Blue)
   - ✅ Buzzer presets (coin, bump, power)
   - ✅ Should now see LED patterns working
   - ✅ Custom tone sliders should work

2. **Sensors Tab**:
   - ✅ BME688 data
   - ✅ Peripherals should show (if API fixed)

3. **Comms Tab** (if firmware supports):
   - Test LoRa, WiFi, BLE, Mesh

## 📌 SIDE-B FIRMWARE (Do Later):

**When you're ready**:
1. Plug Side-B USB into PC (find COM port)
2. Flash MycoBrain_SideB firmware
3. Enables LoRa routing

**For now**: Side-A alone gives you ALL features!

---
**Next**: Restart PC → Start services → Test in browser


