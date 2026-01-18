# MycoBrain Setup Instructions

## Overview

This guide will help you set up MycoBrain connectivity so it works both locally (via USB) and on the sandbox (via Cloudflare tunnel).

## Current Status

✅ **MycoBrain Service**: Running on VM (port 8003, healthy)  
❌ **Cloudflare Tunnel**: Not configured for MycoBrain  
❌ **Website API Routes**: Forwarding configured but service not accessible  
❌ **Service Persistence**: Services may not persist after VM reboot  

---

## Step 1: Move Deprecated Website Files

**Status**: ✅ COMPLETED (Most files moved, app/ directory needs manual move)

The deprecated website files have been moved to `_deprecated_mas_website/` folder. If the `app/` directory still exists, manually move it:

```powershell
# From mycosoft-mas root directory
robocopy "app" "_deprecated_mas_website\app" /E /MOVE /R:3 /W:1
```

Or manually:
1. Create `_deprecated_mas_website/app/` if it doesn't exist
2. Move all contents from `app/` to `_deprecated_mas_website/app/`
3. Delete the now-empty `app/` directory

---

## Step 2: Update Docker Compose

**Action Required**: Remove or comment out the `myca-app` service from `docker-compose.yml`

### Location
`C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\docker-compose.yml`

### What to Remove

Find this section (around line 229-240):

```yaml
  myca-app:
    build:
      context: .
      dockerfile: Dockerfile.next
      target: runner
    ports:
      - "3001:3000"
    environment:
      NODE_ENV: development
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./app:/app/app
```

**Action**: Comment it out or delete it entirely.

**Why**: This service was using the deprecated website and hijacking port 3001.

---

## Step 3: Set Up Cloudflare Tunnel for MycoBrain

### On the VM (192.168.0.187)

**SSH into the VM**:
```bash
ssh mycosoft@192.168.0.187
```

### 3.1 Check Existing Tunnel Configuration

```bash
cat ~/.cloudflared/config.yml
```

### 3.2 Get Your Tunnel ID

If you don't have a tunnel ID, create one:
```bash
cloudflared tunnel create mycobrain-tunnel
```

This will output a tunnel ID (looks like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)

### 3.3 Edit Cloudflare Config

```bash
nano ~/.cloudflared/config.yml
```

Add MycoBrain routes **BEFORE** the catch-all 404 route:

```yaml
tunnel: YOUR_TUNNEL_ID_HERE
credentials-file: /home/mycosoft/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  # MycoBrain API routes (MUST come before catch-all)
  - hostname: sandbox.mycosoft.com
    service: http://localhost:8003
    path: /api/mycobrain
  
  - hostname: sandbox.mycosoft.com
    service: http://localhost:8003
    path: /api/mycobrain/*
  
  # Existing routes for website, MINDEX, etc.
  - hostname: sandbox.mycosoft.com
    service: http://localhost:3000
  
  - hostname: api.sandbox.mycosoft.com
    service: http://localhost:8000
  
  # Catch-all (MUST be last)
  - service: http_status:404
```

**Important**: 
- MycoBrain routes must come **before** the catch-all route
- The `path` matches `/api/mycobrain` and `/api/mycobrain/*`
- This forwards requests to the MycoBrain service on port 8003

### 3.4 Restart Cloudflare Tunnel

```bash
sudo systemctl restart cloudflared
```

### 3.5 Verify Tunnel is Running

```bash
sudo systemctl status cloudflared
```

Check logs:
```bash
sudo journalctl -u cloudflared -f
```

### 3.6 Test MycoBrain Endpoint

From your local machine:
```bash
curl https://sandbox.mycosoft.com/api/mycobrain/health
```

Or test from VM:
```bash
curl http://localhost:8003/health
```

---

## Step 4: Verify Website API Routes

The website already has API routes configured to forward to MycoBrain service.

### Location
`C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\api\mycobrain\`

### Configuration

The routes use environment variable:
```typescript
const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";
```

### Set Environment Variable

#### On VM (for website container)

Edit `docker-compose.always-on.yml` in the `mycosoft-website` service:

```yaml
mycosoft-website:
  environment:
    # ... existing env vars ...
    MYCOBRAIN_SERVICE_URL: http://mycobrain:8003
```

Or if MycoBrain is on host network:
```yaml
MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003
```

**Note**: On the VM, the MycoBrain service is in a different Docker network. You may need to:
1. Add MycoBrain service to the same network as the website, OR
2. Use `host.docker.internal:8003` to access from website container

### Restart Website Container

After updating environment variables:
```bash
cd ~/mycosoft
docker-compose -f docker-compose.always-on.yml up -d mycosoft-website
```

---

## Step 5: Ensure Services Persist After Reboot

### 5.1 Enable Docker Service (Auto-start)

On VM:
```bash
sudo systemctl enable docker
sudo systemctl enable docker-compose@mycosoft.service  # If using systemd service
```

### 5.2 Create Systemd Service for Docker Compose

Create `/etc/systemd/system/mycosoft-stack.service`:

```ini
[Unit]
Description=Mycosoft Always-On Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/mycosoft/mycosoft
ExecStart=/usr/bin/docker-compose -f docker-compose.always-on.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.always-on.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mycosoft-stack.service
sudo systemctl start mycosoft-stack.service
```

### 5.3 Enable Cloudflare Tunnel Service

```bash
sudo systemctl enable cloudflared
```

### 5.4 Verify Services Start on Boot

Test by rebooting the VM:
```bash
sudo reboot
```

After reboot, check services:
```bash
docker ps
sudo systemctl status cloudflared
sudo systemctl status mycosoft-stack  # If you created the service
```

---

## Step 6: Test Complete Setup

### 6.1 Local Development (USB Connection)

MycoBrain connects via USB to your development machine:
- COM port: Check Device Manager for MycoBrain device
- Baud rate: 115200 (default)
- Service: MycoBrain service on localhost:8003 (if running locally)

**Test**:
```bash
curl http://localhost:3000/api/mycobrain/devices
```

### 6.2 Sandbox (Cloudflare Tunnel)

**Test endpoints**:
```bash
# Health check
curl https://sandbox.mycosoft.com/api/mycobrain/health

# Devices
curl https://sandbox.mycosoft.com/api/mycobrain/devices

# Ports
curl https://sandbox.mycosoft.com/api/mycobrain/ports

# Telemetry
curl https://sandbox.mycosoft.com/api/mycobrain/telemetry
```

### 6.3 From Website UI

1. Navigate to: `https://sandbox.mycosoft.com/natureos/devices`
2. Check if MycoBrain devices appear
3. Verify device status and telemetry data

---

## Troubleshooting

### Issue: MycoBrain endpoints return 503/500

**Solutions**:
1. Check MycoBrain service is running: `docker ps | grep mycobrain`
2. Check service health: `curl http://localhost:8003/health`
3. Verify Cloudflare tunnel config has correct routes
4. Check website container can reach MycoBrain service (network configuration)

### Issue: Services don't start after reboot

**Solutions**:
1. Check systemd service status: `sudo systemctl status mycosoft-stack`
2. Check Docker service: `sudo systemctl status docker`
3. Check Cloudflare tunnel: `sudo systemctl status cloudflared`
4. Review logs: `sudo journalctl -u mycosoft-stack -n 50`

### Issue: Website can't reach MycoBrain service

**Solutions**:
1. Ensure both services are on same Docker network OR
2. Use `host.docker.internal:8003` in website environment variables
3. Check firewall rules: `sudo ufw status`
4. Test connectivity: `docker exec mycosoft-website curl http://host.docker.internal:8003/health`

---

## Summary Checklist

- [ ] Move deprecated website files to `_deprecated_mas_website/`
- [ ] Remove `myca-app` service from `docker-compose.yml`
- [ ] Create/update Cloudflare tunnel configuration with MycoBrain routes
- [ ] Restart Cloudflare tunnel service
- [ ] Verify MycoBrain service is running on VM (port 8003)
- [ ] Update website environment variables for MycoBrain service URL
- [ ] Create systemd service for Docker Compose stack
- [ ] Enable services to start on boot
- [ ] Test local USB connection
- [ ] Test sandbox Cloudflare tunnel endpoints
- [ ] Verify services persist after VM reboot

---

## Quick Reference

**VM IP**: 192.168.0.187  
**VM User**: mycosoft  
**MycoBrain Port**: 8003  
**Website Port**: 3000  
**Cloudflare Config**: `~/.cloudflared/config.yml`  
**Docker Compose (Always-On)**: `docker-compose.always-on.yml`  
**Website Location**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
