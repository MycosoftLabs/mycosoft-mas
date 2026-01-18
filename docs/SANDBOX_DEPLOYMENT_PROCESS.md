# Sandbox Deployment Process

**Created**: January 18, 2026  
**Last Updated**: January 18, 2026  
**Author**: Cursor AI Agent

---

> ⚠️ **CRITICAL: Read `DEPLOYMENT_REQUIREMENTS.md` before deploying!**
> 
> Key issues to check:
> 1. Verify cloudflared is NOT running on Windows PC
> 2. Clear Cloudflare cache after every rebuild
> 3. Check Cloudflare Connector Diagnostics shows VM (not Windows)

---

## Overview

This document outlines the complete deployment process for updating `sandbox.mycosoft.com` (VM 103).

## Prerequisites

| Item | Value |
|------|-------|
| **VM ID** | 103 |
| **VM Name** | mycosoft-sandbox |
| **VM IP** | 192.168.0.187 |
| **SSH User** | mycosoft |
| **SSH Password** | Mushroom1!Mushroom1! |
| **Proxmox Host** | 192.168.0.202:8006 |
| **API Token ID** | myca@pve!mas |
| **API Token Secret** | ca23b6c8-5746-46c4-8e36-fc6caad5a9e5 |

## Directory Structure on VM

```
/opt/mycosoft/
├── docker-compose.yml      # MAIN compose file (project: mycosoft-production)
├── .env                    # Environment variables
├── website/                # Website source code (git repo)
├── mas/                    # MAS source code
├── mindex/                 # MINDEX source code
├── data/                   # Data directories
├── logs/                   # Log files
├── config/                 # Configuration files
└── backups/                # Backup files
```

## Docker Architecture

The main `docker-compose.yml` at `/opt/mycosoft/docker-compose.yml` runs with project name `mycosoft-production` and includes:

| Container | Port | Description |
|-----------|------|-------------|
| mycosoft-website | 3000 | Next.js website |
| mindex-api | 8000 | MINDEX FastAPI |
| mindex-postgres | 5432 | PostGIS database |
| mycobrain | 8003 | MycoBrain service |
| mas-orchestrator | - | MAS Orchestrator |
| mas-postgres | - | MAS database |
| redis | 6379 | Redis cache |
| n8n | 5678 | Workflow automation |
| grafana | 3002 | Monitoring |
| prometheus | 9090 | Metrics |
| ollama | - | LLM |
| whisper | - | Speech-to-text |
| tts | - | Text-to-speech |
| openedai-speech | - | OpenAI speech |
| myca-dashboard | 3100 | MYCA Dashboard |
| qdrant | - | Vector database |

## Deployment Script

The automated deployment script is located at:

```
scripts/deploy_paramiko.py
```

### How It Works

1. **Connects via SSH** using Paramiko with password authentication
2. **Pulls latest code** from GitHub to `/opt/mycosoft/website`
3. **Rebuilds website container** using the main docker-compose.yml
4. **Restarts services** as needed
5. **Restarts Cloudflare tunnel** for external access

### Running the Deployment

From Windows PowerShell:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/deploy_paramiko.py
```

## Manual Deployment Steps

If the script fails, deploy manually via SSH:

### 1. Connect to VM

```bash
ssh mycosoft@192.168.0.187
# Password: Mushroom1!Mushroom1!
```

### 2. Pull Latest Code

```bash
cd /opt/mycosoft/website
git fetch origin main
git reset --hard origin/main
```

### 3. Rebuild Website Container

```bash
cd /opt/mycosoft
docker compose -p mycosoft-production build mycosoft-website --no-cache
docker compose -p mycosoft-production up -d mycosoft-website
```

### 4. Restart Cloudflare Tunnel

```bash
sudo systemctl restart cloudflared
```

### 5. Verify Deployment

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
curl -s http://localhost:3000/api/health
```

## Cloudflare Configuration

The Cloudflare tunnel configuration is at:

```
/home/mycosoft/.cloudflared/config.yml
```

Tunnel routes:
- `sandbox.mycosoft.com` → `http://localhost:3000` (Website)
- `api-sandbox.mycosoft.com` → `http://localhost:8000` (MINDEX API)

### Clear Cloudflare Cache

After deployment, clear the cache:
1. Go to https://dash.cloudflare.com
2. Select mycosoft.com domain
3. Caching → Configuration → Purge Everything

## Troubleshooting

### Website Not Loading

1. Check container status:
   ```bash
   docker ps | grep mycosoft-website
   docker logs mycosoft-website --tail 50
   ```

2. Check if port 3000 is accessible:
   ```bash
   curl -s http://localhost:3000/api/health
   ```

### Git Pull Fails

If untracked files block checkout:
```bash
cd /opt/mycosoft/website
git fetch origin main
git reset --hard origin/main
```

Or force fresh clone:
```bash
rm -rf /opt/mycosoft/website
git clone https://github.com/MycosoftLabs/website.git /opt/mycosoft/website
```

### Docker Compose Service Not Found

The website service in `/opt/mycosoft/website/docker-compose.yml` is named `website`, but the main compose file uses `mycosoft-website`. Always use the main compose file:

```bash
cd /opt/mycosoft
docker compose -p mycosoft-production up -d mycosoft-website
```

### Cloudflare Tunnel Not Working

1. Check tunnel status:
   ```bash
   sudo systemctl status cloudflared
   ```

2. View tunnel logs:
   ```bash
   sudo journalctl -u cloudflared -f
   ```

3. Restart tunnel:
   ```bash
   sudo systemctl restart cloudflared
   ```

### 502 Bad Gateway - Tunnel Healthy But No Requests

**Critical Check**: Verify cloudflared is NOT running on Windows!

1. On Windows, check for cloudflared:
   ```powershell
   Get-Process cloudflared -ErrorAction SilentlyContinue
   ```

2. If running, STOP IT:
   ```powershell
   taskkill /F /IM cloudflared.exe
   sc.exe stop cloudflared
   ```

3. Check Cloudflare Connector Diagnostics in Zero Trust dashboard:
   - Should show Private IP: `192.168.0.187` (VM)
   - Should show Platform: `linux_amd64`
   - Should NOT show: `192.168.0.172` (Windows) or `MycoComp`

4. Check tunnel is receiving requests:
   ```bash
   curl -s http://127.0.0.1:20241/metrics | grep tunnel_total_requests
   ```
   If `tunnel_total_requests 0` - Cloudflare is routing to wrong connector.

5. Restart VM tunnel after stopping Windows cloudflared:
   ```bash
   sudo systemctl restart cloudflared
   ```

## API Access Methods

### Method 1: Paramiko SSH (Recommended)

Uses Python's paramiko library for SSH with password auth.

```python
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.187", username="mycosoft", password="Mushroom1!Mushroom1!")
stdin, stdout, stderr = ssh.exec_command("docker ps")
```

### Method 2: Proxmox QEMU Guest Agent

Uses Proxmox API to execute commands directly on VM.

**Limitations**: Only works for simple commands without shell features (no `&&`, pipes, etc.).

```python
import requests
headers = {"Authorization": f"PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
requests.post("https://192.168.0.202:8006/api2/json/nodes/pve/qemu/103/agent/exec",
              headers=headers, data={"command": "/bin/ls"}, verify=False)
```

### Method 3: Direct SSH (Windows)

Requires SSH key setup or interactive password entry.

```powershell
ssh mycosoft@192.168.0.187 "docker ps"
```

## Test URLs

After deployment, verify these URLs:

- https://sandbox.mycosoft.com - Homepage
- https://sandbox.mycosoft.com/natureos - NatureOS Dashboard
- https://sandbox.mycosoft.com/natureos/devices - Device Manager
- https://sandbox.mycosoft.com/admin - Super Admin (requires auth)
- https://sandbox.mycosoft.com/apps - Applications

## Related Documentation

- `docs/VM103_DEPLOYMENT_COMPLETE.md` - VM setup details
- `docs/MYCOSOFT_STACK_DEPLOYMENT.md` - Full stack deployment
- `docs/SESSION_VM_CREATION_JAN17_2026.md` - VM creation history
- `docs/CLOUDFLARE_TUNNEL_SETUP.md` - Tunnel configuration

---

*Last successful deployment: January 18, 2026 02:20 UTC*
*Last updated with 502 troubleshooting: January 18, 2026*
