# MycoBrain Bridge Setup Guide

**Purpose**: Connect the VM sandbox website to the local Windows MycoBrain service

## Current Status

| Component | Status | Details |
|-----------|--------|---------|
| **Windows MycoBrain Service** | ✅ Running | `http://192.168.0.172:8003` |
| **Device Connected** | ✅ COM7 | ESP32-S3, Firmware 2.0.0, 2x BME688 |
| **Local Website** | ✅ Working | `http://localhost:3000` |
| **Sandbox Website** | ❌ Not Connected | Pointing to localhost:8003 (VM) |

## Step 1: Windows Firewall (Run as Administrator)

Open **PowerShell as Administrator** and run:

```powershell
netsh advfirewall firewall add rule name="MycoBrain Service" dir=in action=allow protocol=TCP localport=8003 remoteip=192.168.0.0/24
```

## Step 2: SSH to VM and Update Configuration

```bash
# SSH into the VM
ssh mycosoft@192.168.0.187
# Password: Mushroom1!Mushroom1!

# Navigate to mycosoft directory
cd /opt/mycosoft

# Find current MycoBrain configuration
grep -r "MYCOBRAIN_SERVICE_URL" .

# Edit the docker-compose or .env file
# Change: MYCOBRAIN_SERVICE_URL=http://localhost:8003
# To:     MYCOBRAIN_SERVICE_URL=http://192.168.0.172:8003

# Option A: If using docker-compose.yml environment
nano docker-compose.always-on.yml
# Find the mycosoft-website service and update:
#   environment:
#     - MYCOBRAIN_SERVICE_URL=http://192.168.0.172:8003

# Option B: If using .env file
echo "MYCOBRAIN_SERVICE_URL=http://192.168.0.172:8003" >> .env

# Restart the website container
docker-compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website

# Verify the change
docker logs mycosoft-website --tail 20
```

## Step 3: Verify Connection

Test that the VM can reach the Windows MycoBrain service:

```bash
# From VM
curl http://192.168.0.172:8003/health
# Expected: {"status":"ok","timestamp":"...","devices_connected":1}

curl http://192.168.0.172:8003/devices
# Expected: Device details with COM7 connected
```

## Step 4: Test Sandbox Website

1. Open: https://sandbox.mycosoft.com/natureos/devices
2. Should show MycoBrain Gateway on COM7
3. Test LED and buzzer controls

## Architecture After Fix

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │   Cloudflare    │                           │
│                   │   Edge Network  │                           │
│                   └────────┬────────┘                           │
│                            │                                     │
│              ┌─────────────┼─────────────┐                      │
│              ▼                           ▼                      │
│    sandbox.mycosoft.com          mycosoft.com (prod)           │
│                                                                  │
└──────────────┬───────────────────────────────────────────────────┘
               │ Cloudflare Tunnel
               │
┌──────────────▼───────────────────────────────────────────────────┐
│              VM 103 (192.168.0.187)                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Website Container (Next.js)                                │  │
│  │  MYCOBRAIN_SERVICE_URL=http://192.168.0.172:8003 ──────────┼──┼──┐
│  └────────────────────────────────────────────────────────────┘  │  │
└───────────────────────────────────────────────────────────────────┘  │
                                                                       │
               ┌───────────────────────────────────────────────────────┘
               │ Local Network (192.168.0.x)
               ▼
┌───────────────────────────────────────────────────────────────────┐
│              Windows 11 Dev Machine (192.168.0.172)               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  MycoBrain Service (Python/FastAPI)                         │  │
│  │  Port: 8003                                                  │  │
│  │         │                                                    │  │
│  │         ▼                                                    │  │
│  │  ┌─────────────┐                                            │  │
│  │  │   COM7      │ USB Serial                                 │  │
│  │  │  ESP32-S3   │ MycoBrain Device                          │  │
│  │  │  2x BME688  │ Sensors                                    │  │
│  │  └─────────────┘                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### VM can't reach Windows
```bash
# Test connectivity
ping 192.168.0.172
telnet 192.168.0.172 8003

# Check Windows firewall
# On Windows (admin):
netsh advfirewall firewall show rule name="MycoBrain Service"
```

### Website still shows "No MycoBrain"
```bash
# Verify environment variable is set
docker exec mycosoft-website printenv | grep MYCOBRAIN

# Check container logs
docker logs mycosoft-website --tail 50
```

---
*Created: January 17, 2026*
*Windows IP: 192.168.0.172*
*VM IP: 192.168.0.187*
