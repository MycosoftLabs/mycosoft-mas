# Tailscale Remote Device Setup Guide

**Date:** February 9, 2026
**Author:** Cursor/MYCA
**Status:** Complete
**Purpose:** Configure Tailscale VPN for remote MycoBrain devices to connect to the Mycosoft Device Network

---

## Overview

This guide explains how to set up Tailscale VPN on a remote machine so that MycoBrain devices can:
1. Automatically register with the central MAS Device Registry
2. Send heartbeats and telemetry to the Mycosoft system
3. Receive commands from the central Device Manager
4. Appear in the Network Devices tab on the website

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Tailscale VPN Network                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐         ┌────────────────────┐                  │
│  │  Remote Machine    │         │  MAS VM            │                  │
│  │  (Beto's PC)       │         │  192.168.0.188     │                  │
│  │                    │         │                    │                  │
│  │  MycoBrain Service │ ──────► │  Device Registry   │                  │
│  │  :8003             │Heartbeat│  /api/devices      │                  │
│  │                    │ ◄────── │                    │                  │
│  │  Tailscale IP:     │ Command │  :8001             │                  │
│  │  100.x.x.x         │         │                    │                  │
│  └────────────────────┘         └────────────────────┘                  │
│           │                              │                               │
│           │                              │                               │
│           ▼                              ▼                               │
│  ┌────────────────────┐         ┌────────────────────┐                  │
│  │  MycoBrain Board   │         │  Website           │                  │
│  │  ESP32-S3          │         │  Device Manager    │                  │
│  │  USB Serial        │         │  Network Tab       │                  │
│  └────────────────────┘         └────────────────────┘                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Install Tailscale

### Windows

```powershell
# Option 1: Using winget
winget install Tailscale.Tailscale

# Option 2: Download installer
# https://tailscale.com/download/windows
```

### macOS

```bash
brew install tailscale
```

### Linux

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

---

## Step 2: Join the Mycosoft Tailnet

1. **Open Tailscale app** (system tray on Windows, menu bar on macOS)
2. **Click "Log in"**
3. You'll be directed to a browser to authenticate
4. **Contact Mycosoft admin** to get an invite to the Mycosoft tailnet
5. Once invited, your machine will appear in the tailnet

### Verify Connection

```powershell
# Check your Tailscale IP
tailscale ip -4

# Check connection status
tailscale status

# Verify you can reach MAS VM
ping 192.168.0.188
```

Your Tailscale IP will look like `100.x.x.x` - this is the address other tailnet members can use to reach your machine.

---

## Step 3: Configure MycoBrain Service for Network Registration

The MycoBrain service needs environment variables to enable heartbeat registration:

### Create/Edit `.env` file

In your `mycosoft-mas` repository root, create or edit `.env`:

```properties
# MycoBrain Network Registration
MYCOBRAIN_HEARTBEAT_ENABLED=true
MYCOBRAIN_HEARTBEAT_INTERVAL=30
MYCOBRAIN_DEVICE_NAME=Beto-MycoBrain
MYCOBRAIN_DEVICE_LOCATION=Remote-Beto
MAS_REGISTRY_URL=http://192.168.0.188:8001

# Optional: Public host for external access
# Leave empty to auto-detect Tailscale IP
MYCOBRAIN_PUBLIC_HOST=
```

### Environment Variables Explained

| Variable | Default | Description |
|----------|---------|-------------|
| `MYCOBRAIN_HEARTBEAT_ENABLED` | `true` | Enable heartbeat registration with MAS |
| `MYCOBRAIN_HEARTBEAT_INTERVAL` | `30` | Seconds between heartbeats |
| `MYCOBRAIN_DEVICE_NAME` | `Remote-MycoBrain` | Friendly name for your device |
| `MYCOBRAIN_DEVICE_LOCATION` | `remote` | Location tag for your setup |
| `MAS_REGISTRY_URL` | `http://192.168.0.188:8001` | MAS Device Registry URL |
| `MYCOBRAIN_PUBLIC_HOST` | (auto-detect) | Override auto-detected address |

---

## Step 4: Start MycoBrain Service

```powershell
cd C:\Mycosoft\mycosoft-mas

# Start the service
python services/mycobrain/mycobrain_service_standalone.py
```

You should see output like:

```
INFO:     Started server on http://0.0.0.0:8003
INFO:     Heartbeat system enabled
INFO:     Using Tailscale IP: 100.x.x.x
INFO:     Will send heartbeats to http://192.168.0.188:8001/api/devices/register
```

---

## Step 5: Connect Your Device

```powershell
# Connect your MycoBrain board (replace COM3 with your port)
Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM3" -Method Post
```

After connecting, the service will automatically:
1. Send a heartbeat to the MAS Device Registry
2. Register your device with its Tailscale IP and port
3. Continue sending heartbeats every 30 seconds

---

## Step 6: Verify Registration

### Check MAS Device Registry

```powershell
# List all registered devices
Invoke-RestMethod -Uri "http://192.168.0.188:8001/api/devices" -Method Get
```

Your device should appear with:
- `connection_type: "tailscale"`
- `host: "100.x.x.x"` (your Tailscale IP)
- `status: "online"`

### Check Website Device Manager

1. Open https://sandbox.mycosoft.com/natureos/devices
2. Click the **Network** tab
3. Your device should appear in the list

---

## Automatic Setup Script

For convenience, use the automated setup script:

```powershell
cd C:\Mycosoft\mycosoft-mas\scripts

# Run the setup script
.\mycobrain-remote-setup.ps1 -InstallTailscale -DeviceName "Beto-MycoBrain" -Location "Remote-Beto"
```

The script will:
1. Optionally install Tailscale
2. Clone/update the mycosoft-mas repository
3. Install Python dependencies
4. Create the `.env` file with your settings
5. Optionally start the MycoBrain service

---

## Troubleshooting

### Heartbeat Not Sending

1. **Check environment variables**:
   ```powershell
   $env:MYCOBRAIN_HEARTBEAT_ENABLED
   ```

2. **Check MAS connectivity**:
   ```powershell
   Invoke-RestMethod -Uri "http://192.168.0.188:8001/health" -Method Get
   ```

3. **Check Tailscale status**:
   ```powershell
   tailscale status
   ```

### Device Not Appearing in Network Tab

1. **Verify heartbeat is sending** - check service logs for "Heartbeat sent successfully"
2. **Check device is connected** - list local devices: `http://localhost:8003/devices`
3. **Check registry** - list registered devices: `http://192.168.0.188:8001/api/devices`

### Commands Not Working

The MAS forwards commands to your local service via Tailscale. Ensure:
1. Your Tailscale IP is correct in the registry
2. Port 8003 is not blocked by firewall
3. The device is connected locally

### Tailscale IP Not Detected

If auto-detection fails, set the IP manually:

```properties
MYCOBRAIN_PUBLIC_HOST=100.x.x.x
```

Get your Tailscale IP with:
```powershell
tailscale ip -4
```

---

## Alternative: Cloudflare Tunnel

If you cannot use Tailscale (e.g., corporate network restrictions), use Cloudflare Tunnel instead:

### Install cloudflared

```powershell
winget install Cloudflare.cloudflared
```

### Create Tunnel

```powershell
# Create a persistent tunnel
cloudflared tunnel create mycobrain

# Route traffic to your local service
cloudflared tunnel route dns mycobrain mycobrain-beto.mycosoft.com

# Start the tunnel
cloudflared tunnel run mycobrain --url http://localhost:8003
```

### Configure Service

Set your public host to the Cloudflare tunnel URL:

```properties
MYCOBRAIN_PUBLIC_HOST=https://mycobrain-beto.mycosoft.com
```

---

## Security Considerations

1. **Tailscale ACLs**: The Mycosoft tailnet should have ACL rules to restrict access to necessary ports only
2. **Firewall**: Only port 8003 needs to be accessible, and only from tailnet members
3. **Authentication**: Future versions will require device authentication tokens
4. **Encryption**: Tailscale provides end-to-end encryption for all traffic

---

## Related Documentation

| Document | Path |
|----------|------|
| Beto Setup Guide | `docs/MYCOBRAIN_BETO_SETUP_GUIDE_FEB09_2026.md` |
| Device Registry API | `docs/API_CATALOG_FEB04_2026.md` |
| MycoBrain Service | `services/mycobrain/mycobrain_service_standalone.py` |
| Remote Setup Script | `scripts/mycobrain-remote-setup.ps1` |
| Tailscale Utils | `services/mycobrain/tailscale_utils.py` |

---

## Quick Reference

### Commands

```powershell
# Check Tailscale IP
tailscale ip -4

# Check Tailscale status
tailscale status

# Start MycoBrain service
python services/mycobrain/mycobrain_service_standalone.py

# Connect device
Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM3" -Method Post

# List registered devices (on MAS)
Invoke-RestMethod -Uri "http://192.168.0.188:8001/api/devices" -Method Get
```

### URLs

| Service | URL |
|---------|-----|
| Local MycoBrain Service | http://localhost:8003 |
| MAS Device Registry | http://192.168.0.188:8001/api/devices |
| Website Device Manager | https://sandbox.mycosoft.com/natureos/devices |
