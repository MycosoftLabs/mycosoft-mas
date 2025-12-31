# MycoBrain COM5 Setup Complete

## ✅ Status

- **MycoBrain Service**: Running on port 8003
- **Device Port**: COM5 (USB-C)
- **Service Health**: Online
- **Device Discovery**: Active

## 🔧 Changes Made

1. **Fixed Device Discovery API** - Updated to use port 8003 (was 8765)
2. **Updated Default Port** - Changed from COM4 to COM5
3. **Added Service Status Indicator** - Device Network page now shows MycoBrain service status
4. **Removed Fake Devices** - Overview devices tab now only shows real devices from APIs

## 📍 Device Location

- **Port**: COM5
- **Connection**: USB-C
- **Device**: MycoBrain board
- **Status**: Agent currently debugging (port may be locked)

## 🚀 Next Steps

### Connect Device via Website

1. Go to **http://localhost:3000/natureos/devices**
2. Click "Scan for Devices" or use quick connect to COM5
3. Device should appear in both:
   - Overview → Devices tab
   - Infrastructure → Device Network

### If Port is Locked

If COM5 is locked by the debugging agent:
1. Close the agent/debugger
2. Try connecting again via the website
3. Or use the API directly:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM5" -Method POST -ContentType "application/json" -Body '{"port":"COM5","baudrate":115200}'
   ```

## 🔍 Service Endpoints

- **Health**: http://localhost:8003/health
- **Devices**: http://localhost:8003/devices
- **Ports**: http://localhost:8003/ports
- **Connect**: POST http://localhost:8003/devices/connect/COM5

## 📝 Notes

- Service runs independently of Cursor
- Watchdog monitors and restarts service if it crashes
- All fake/sample devices removed from Overview
- Only real devices from MycoBrain service and MINDEX are shown

























