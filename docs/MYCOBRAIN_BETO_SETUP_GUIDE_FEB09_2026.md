# MycoBrain Setup Guide for Beto
**Date:** February 9, 2026  
**Author:** Cursor/MYCA  
**Purpose:** Complete guide to set up a MycoBrain board on a remote machine and connect to the Mycosoft Device Network

---

## Overview

This guide will help you:
1. Set up your development environment
2. Upload the MycoBrain firmware to your ESP32-S3 board
3. Run the MycoBrain service on your machine
4. Connect to the Device Manager and broadcast to the network

---

## Prerequisites

### Hardware
- MycoBrain ESP32-S3 board with dual BME688 sensors
- USB data cable (not charge-only)
- Windows PC

### Software to Install
1. **Arduino IDE 2.x** - https://www.arduino.cc/en/software
2. **Python 3.10+** - https://www.python.org/downloads/
3. **Git** - https://git-scm.com/downloads
4. **Node.js 18+** (optional, for local website) - https://nodejs.org/

---

## Step 1: Install Arduino IDE and ESP32 Support

### 1.1 Install Arduino IDE
Download and install Arduino IDE 2.x from https://www.arduino.cc/en/software

### 1.2 Add ESP32 Board Support
1. Open Arduino IDE
2. Go to **File → Preferences**
3. In "Additional Boards Manager URLs", add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click **OK**
5. Go to **Tools → Board → Boards Manager**
6. Search for "esp32"
7. Install **esp32 by Espressif Systems** (version 2.0.x or later)

### 1.3 Install Required Libraries
Go to **Sketch → Include Library → Manage Libraries** and install:
- ArduinoJson (by Benoit Blanchon)
- Adafruit NeoPixel

---

## Step 2: Clone the Repository

Open PowerShell and run:

```powershell
# Create a workspace folder
mkdir C:\Mycosoft
cd C:\Mycosoft

# Clone the MAS repository
git clone https://github.com/mycosoft/mycosoft-mas.git
cd mycosoft-mas
```

---

## Step 3: Connect Your MycoBrain Board

1. Connect your MycoBrain board via USB
2. Open Device Manager (Win+X → Device Manager)
3. Look under "Ports (COM & LPT)" for "USB Serial Device" or "Silicon Labs CP210x"
4. Note the COM port number (e.g., COM3, COM7)

---

## Step 4: Upload Firmware

### 4.1 Open Firmware in Arduino IDE

**RECOMMENDED FIRMWARE** (choose one):

| Firmware | Path | Description |
|----------|------|-------------|
| **Production** (recommended) | `firmware/MycoBrain_SideA/MycoBrain_SideA.ino` | Clean production firmware with website integration |
| **Garrett's Working** | `mycobrain/firmware/MycoBrain_SideA/MycoBrain_SideA_WORKING_DEC29.ino` | Proven stable with full BSEC2 and morgio sounds |
| **startHERE** | `mycobrain/firmware/MycoBrain_SideA/startHERE_ESP32AB_BSEC2_WORKING_DUAL_morgio_BLOCK.ino` | Original Garrett code with dual BME688 BSEC2 |

The firmware running on the current board is `mycobrain.sideA.bsec2` version 2.0.0 with BSEC2 support.

1. Open Arduino IDE
2. Go to **File → Open**
3. Navigate to one of the firmware paths above (Production recommended)
4. Click **Open**

### 4.2 Configure Arduino IDE Settings

Go to **Tools** and set:

| Setting | Value |
|---------|-------|
| Board | ESP32-S3 Dev Module |
| Port | YOUR_COM_PORT (e.g., COM3) |
| Upload Speed | 115200 |
| CPU Frequency | 240MHz |
| Flash Mode | QIO |
| Flash Size | 4MB (32Mb) |
| Partition Scheme | Default 4MB with spiffs |
| PSRAM | Disabled |
| USB CDC On Boot | Enabled |
| Erase All Flash Before Sketch Upload | **Enabled** ← CRITICAL! |

### 4.3 Boot Mode Procedure (CRITICAL - Required Before EVERY Upload)

The ESP32-S3 requires manual boot mode entry. Follow these steps **EXACTLY**:

1. **UNPLUG** the USB cable from your MycoBrain board
2. **WAIT 30 seconds** (let capacitors discharge completely)
3. **HOLD** the **BOOT** button on the board (small button, usually labeled BOOT or 0)
4. **WHILE HOLDING BOOT**, plug the USB cable back in
5. **KEEP HOLDING** BOOT for 5 full seconds (count: one-Mississippi, two-Mississippi...)
6. **RELEASE** the BOOT button
7. **WAIT 2 seconds** (don't touch anything)
8. **IMMEDIATELY** click the Upload button in Arduino IDE (→ arrow)

### 4.4 Verify Upload Success

You should see:
- "Connecting..." changes to "Writing at 0x..."
- Progress bar appears
- "Done uploading" message

If you see "Connecting......." forever:
- Boot mode failed - repeat Step 4.3 more carefully
- Try holding BOOT for 10 seconds instead of 5
- Try different USB port (USB 2.0 preferred)

### 4.5 Test Firmware

1. Open **Tools → Serial Monitor**
2. Set baud rate to **115200** (dropdown in bottom-right)
3. Press the **RESET** button on the board
4. You should see the SuperMorgIO POST screen and hear the boot jingle
5. Type `help` and press Enter - you should see available commands
6. Type `status` - you should see device info with sensor readings

---

## Step 5: Install Python Dependencies

Open PowerShell and run:

```powershell
cd C:\Mycosoft\mycosoft-mas

# Install pyserial
pip install pyserial fastapi uvicorn pydantic
```

---

## Step 6: Start MycoBrain Service

The MycoBrain service runs on your machine and provides a REST API for the Device Manager.

```powershell
cd C:\Mycosoft\mycosoft-mas

# Start the service (runs on http://localhost:8003)
python services/mycobrain/mycobrain_service_standalone.py
```

Leave this window open - the service needs to keep running.

### Verify Service is Running

Open a new PowerShell window:
```powershell
Invoke-RestMethod -Uri "http://localhost:8003/health" -Method Get
```

Expected output:
```json
{
  "status": "ok",
  "service": "mycobrain",
  "version": "2.2.0"
}
```

---

## Step 7: Connect Your Device

```powershell
# Replace COM3 with your actual COM port
Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM3" -Method Post
```

Expected output:
```json
{
  "status": "connected",
  "device_id": "mycobrain-COM3",
  "port": "COM3"
}
```

---

## Step 8: Test Device Commands

```powershell
# Test status (replace COM3 with your port)
$body = '{"command":{"cmd":"status"}}'
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM3/command" -Method Post -Body $body -ContentType "application/json"

# Test LED (red)
$body = '{"command":{"cmd":"led rgb 255 0 0"}}'
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM3/command" -Method Post -Body $body -ContentType "application/json"

# Test coin sound
$body = '{"command":{"cmd":"coin"}}'
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM3/command" -Method Post -Body $body -ContentType "application/json"

# Test morgio jingle
$body = '{"command":{"cmd":"morgio"}}'
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM3/command" -Method Post -Body $body -ContentType "application/json"
```

---

## Step 9: Access Device Manager

### Option A: Use the Website Dev Server (Recommended for Testing)

```powershell
# Clone the website repo if you haven't
cd C:\Mycosoft
git clone https://github.com/mycosoft/website.git
cd website

# Install dependencies
npm install

# Start dev server (port 3010)
npm run dev:next-only
```

Then open your browser to:
```
http://localhost:3010/natureos/devices?device=COM3
```

### Option B: Use Sandbox (Production)

Open your browser to:
```
https://sandbox.mycosoft.com/natureos/devices?device=COM3
```

Note: For the Sandbox to see your local device, you need to ensure your MycoBrain service is accessible. This typically requires:
- Your machine and the Sandbox VM on the same network, OR
- Port forwarding/tunnel to expose your localhost:8003

---

## Connecting Your Device to the Network (Remote Access)

For Beto or other remote users to have their MycoBrain visible in the central Device Network, the MycoBrain service now includes **automatic heartbeat registration**. Your device will appear in the Device Manager's **Network** tab.

### How It Works

1. Your MycoBrain service sends periodic **heartbeats** to the MAS Device Registry
2. The registry tracks your device's IP, port, and status
3. Your device appears in the website's Device Manager under the **Network** tab
4. Commands can be sent from the central UI to your remote device

### Step 1: Install Tailscale (Recommended)

```powershell
winget install Tailscale.Tailscale
```

Then log in and join the Mycosoft tailnet (contact admin for invite).

See: [Tailscale Remote Device Guide](./TAILSCALE_REMOTE_DEVICE_GUIDE_FEB09_2026.md)

### Step 2: Configure Environment Variables

Create a `.env` file in your `mycosoft-mas` root:

```properties
# Enable heartbeat registration
MYCOBRAIN_HEARTBEAT_ENABLED=true
MYCOBRAIN_HEARTBEAT_INTERVAL=30
MYCOBRAIN_DEVICE_NAME=Beto-MycoBrain
MYCOBRAIN_DEVICE_LOCATION=Remote-Beto
MAS_REGISTRY_URL=http://192.168.0.188:8001

# Leave empty to auto-detect Tailscale IP
MYCOBRAIN_PUBLIC_HOST=
```

### Step 3: Start Service and Connect Device

```powershell
# Start the service (heartbeats will auto-start)
python services/mycobrain/mycobrain_service_standalone.py

# Connect your device
Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM3" -Method Post
```

### Step 4: Verify in Device Manager

1. Open https://sandbox.mycosoft.com/natureos/devices
2. Click the **Network** tab
3. Your device should appear with status "online" and connection type "tailscale"

### Alternative: Cloudflare Tunnel

If Tailscale isn't available:

```powershell
winget install Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8003
```

Set `MYCOBRAIN_PUBLIC_HOST=https://your-tunnel-url` in your `.env`.

### Alternative: Local Network Only

If you're on the same network as the Mycosoft VMs (192.168.0.x):
1. Your local service is accessible at YOUR_IP:8003
2. The heartbeat system auto-detects your LAN IP
3. Your device appears with connection type "lan"

### Automated Setup Script

Use the automated setup script for quick configuration:

```powershell
cd C:\Mycosoft\mycosoft-mas\scripts
.\mycobrain-remote-setup.ps1 -InstallTailscale -DeviceName "Beto-MycoBrain" -Location "Remote-Beto"
```

### Troubleshooting Network Registration

| Issue | Solution |
|-------|----------|
| Device not appearing | Check heartbeat logs for "Heartbeat sent successfully" |
| Commands not working | Verify Tailscale IP is correct, port 8003 accessible |
| "Service offline" status | Device hasn't sent heartbeat in 60+ seconds |
| Wrong IP detected | Set `MYCOBRAIN_PUBLIC_HOST` manually |

---

## Step 10: Device Manager Features

Once connected, you can:

### Sensors Tab
- View real-time BME688 sensor readings
- Temperature, humidity, pressure, gas resistance
- IAQ (Indoor Air Quality) index

### Controls Tab
- **LED Control**: Set colors (Red, Green, Blue, etc.)
- **Buzzer Presets**: Coin, Bump, Power, 1-Up, Morgio sounds
- **Custom Tone**: Set frequency and duration

### Console Tab
- Send raw serial commands
- View device responses

### Diagnostics Tab
- I2C scan
- System status
- Firmware info

---

## Firmware Features

### Supported Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `status` | Device status and sensor info |
| `led rgb R G B` | Set LED color (0-255 each) |
| `coin` | Mario coin pickup sound |
| `morgio` | SuperMorgIO jingle |
| `bump` | Bump/collision sound |
| `power` | Power-up sound |
| `1up` | Extra life sound |
| `scan` | I2C device scan |

### Hardware Pin Configuration

| Function | GPIO | Notes |
|----------|------|-------|
| I2C SDA | GPIO5 | BME688 sensors |
| I2C SCL | GPIO4 | BME688 sensors |
| NeoPixel | GPIO15 | SK6805 single LED |
| Buzzer | GPIO16 | PWM piezo |
| MOSFET 1 | GPIO12 | Digital output |
| MOSFET 2 | GPIO13 | Digital output |
| MOSFET 3 | GPIO14 | Digital output |
| Analog 1 | GPIO6 | ADC input |
| Analog 2 | GPIO7 | ADC input |
| Analog 3 | GPIO10 | ADC input |
| Analog 4 | GPIO11 | ADC input |

---

## Troubleshooting

### "Device not found" or "Failed to connect"
- Check COM port in Device Manager
- Verify USB cable is data-capable (not charge-only)
- Try different USB port (USB 2.0 preferred)
- Restart the MycoBrain service

### Upload fails with "Connecting........"
- Boot mode failed - follow Step 4.3 more carefully
- Hold BOOT button longer (10 seconds)
- Try lower upload speed (9600)
- Close Serial Monitor before uploading

### No sensor readings
- Check BME688 sensors are connected
- Run `scan` command to verify I2C devices
- Should show addresses 0x76 and 0x77

### LED or buzzer not working
- Check pin configuration in firmware
- Verify correct GPIO connections
- Test with serial commands first

### Service not responding
- Check if Python process is running
- Verify port 8003 is not blocked by firewall
- Restart the service

---

## Quick Reference

### Start Everything

```powershell
# Terminal 1: Start MycoBrain Service
cd C:\Mycosoft\mycosoft-mas
python services/mycobrain/mycobrain_service_standalone.py

# Terminal 2: Connect Device
Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM3" -Method Post

# Terminal 3: Start Website (optional)
cd C:\Mycosoft\website
npm run dev:next-only
```

### URLs

| Service | URL |
|---------|-----|
| MycoBrain Service | http://localhost:8003 |
| Website Dev | http://localhost:3010 |
| Device Manager | http://localhost:3010/natureos/devices?device=COM3 |
| Sandbox | https://sandbox.mycosoft.com |

---

## Support

If you have issues:
1. Check this guide's troubleshooting section
2. Review the firmware docs in `firmware/*.md`
3. Contact the team on Slack/Discord

---

## Document Index

| Document | Path |
|----------|------|
| This guide | `docs/MYCOBRAIN_BETO_SETUP_GUIDE_FEB09_2026.md` |
| Tailscale Remote Guide | `docs/TAILSCALE_REMOTE_DEVICE_GUIDE_FEB09_2026.md` |
| Remote Setup Script | `scripts/mycobrain-remote-setup.ps1` |
| Tailscale Utilities | `services/mycobrain/tailscale_utils.py` |
| Device Registry API | `mycosoft_mas/core/routers/device_registry_api.py` |
| Skill | `.cursor/skills/mycobrain-setup/SKILL.md` |
| Subagent | `.cursor/agents/device-firmware.md` |
| Arduino Settings | `firmware/ARDUINO_IDE_SETTINGS.md` |
| Upload Guide | `firmware/STEP_BY_STEP_UPLOAD.md` |
| Boot Mode Fix | `firmware/BOOT_MODE_FIX.md` |
| Firmware | `firmware/MycoBrain_SideA/MycoBrain_SideA.ino` |
| Service | `services/mycobrain/mycobrain_service_standalone.py` |
