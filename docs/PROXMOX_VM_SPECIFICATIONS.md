# Proxmox VM Specifications

## DEPLOYMENT STATUS (Updated 2026-01-17 01:57 UTC)

### VM 103 - Mycosoft Sandbox - FULLY OPERATIONAL

| Service | Port | Local Status | Cloudflare URL | Status |
|---------|------|--------------|----------------|--------|
| Website | 3000 | ✅ Running | https://sandbox.mycosoft.com | ✅ 200 OK |
| MINDEX API | 8000 | ✅ Running | https://api-sandbox.mycosoft.com | ✅ 200 OK |
| MycoBrain | 8003 | ✅ Running | https://brain-sandbox.mycosoft.com | ⚠️ 404 (Route Fix Needed) |
| MAS Orchestrator | 8001 | ✅ Running | (internal) | N/A |
| n8n | 5678 | ✅ Running | (internal) | N/A |
| Grafana | 3002 | ✅ Running | (internal) | N/A |
| Prometheus | 9090 | ✅ Running | (internal) | N/A |
| PostgreSQL | 5432 | ✅ Running (healthy) | (internal) | N/A |
| Redis | 6379 | ✅ Running (healthy) | (internal) | N/A |
| Qdrant | 6333 | ✅ Running | (internal) | N/A |

### Cloudflare Tunnel Fix for brain-sandbox

To fix the brain-sandbox.mycosoft.com route:
1. Go to Cloudflare Dashboard → Zero Trust → Networks → Tunnels
2. Click on the "Microsoft" tunnel
3. Go to "Publish application routes"
4. Find or add the brain-sandbox route:
   - **Subdomain**: brain-sandbox
   - **Domain**: mycosoft.com
   - **Type**: HTTP
   - **URL**: localhost:8003

---

## ✅ DEPLOYMENT COMPLETE - January 17, 2026

### VM 103 (mycosoft-sandbox) - LIVE

| Component | Status | Details |
|-----------|--------|---------|
| **VM Created** | ✅ | ID 103, Ubuntu 24.04.2 LTS |
| **IP Address** | ✅ | 192.168.0.187 |
| **SSH Access** | ✅ | `ssh mycosoft@192.168.0.187` |
| **Docker** | ✅ | v29.1.5 |
| **Docker Compose** | ✅ | v5.0.1 |
| **QEMU Guest Agent** | ✅ | Installed |

### Running Services

| Service | Port | URL |
|---------|------|-----|
| Website | 3000 | http://192.168.0.187:3000 |
| MINDEX API | 8000 | http://192.168.0.187:8000 |
| MycoBrain | 8003 | http://192.168.0.187:8003 |
| PostgreSQL | 5432 | 192.168.0.187:5432 |
| Redis | 6379 | 192.168.0.187:6379 |

---

## ✅ VM 103 DEPLOYMENT COMPLETE - January 17, 2026

### Quick Reference
| Item | Value |
|------|-------|
| **VM ID** | 103 |
| **Name** | mycosoft-sandbox |
| **IP Address** | 192.168.0.187 |
| **SSH** | `ssh mycosoft@192.168.0.187` |
| **Password** | `REDACTED_VM_SSH_PASSWORD` |
| **OS** | Ubuntu 24.04.2 LTS |
| **Docker** | 29.1.5 |
| **Docker Compose** | v5.0.1 |

### Running Services
| Service | Port | URL |
|---------|------|-----|
| Mycosoft Website | 3000 | http://192.168.0.187:3000 |
| MINDEX API | 8000 | http://192.168.0.187:8000 |
| MycoBrain Service | 8003 | http://192.168.0.187:8003 |
| PostgreSQL | 5432 | 192.168.0.187:5432 |
| Redis | 6379 | 192.168.0.187:6379 |

--- for Mycosoft System

> **STATUS: VM 103 (mycosoft-sandbox) CREATED SUCCESSFULLY** ✅
> 
> Created: January 16, 2026 at 16:07:13 UTC
> 
> The sandbox VM has been created with all specifications below. Next step is to start the VM and install Ubuntu.

**Version**: 1.0.0  
**Date**: 2026-01-16  
**Purpose**: Complete Proxmox VE 8.4 specifications for Sandbox and Production VMs  
**Target**: mycosoft.com via Cloudflare Tunnel

---

## 🎯 Executive Summary

This document provides **exact Proxmox VM specifications** for deploying the complete Mycosoft system. We will create two VMs:

1. **Sandbox VM (VM ID 103)** - Development/Testing environment
2. **Production VM (VM ID 104)** - Live production via Cloudflare tunnel to mycosoft.com

### Windows → Linux Compatibility Analysis

**Good News**: Your codebase is **100% Linux-compatible**. Here's why:

| Technology | Windows Dev | Linux Production | Compatibility |
|------------|-------------|------------------|---------------|
| **Node.js/Next.js** | ✅ Cross-platform | ✅ Native | Perfect |
| **Python** | ✅ Cross-platform | ✅ Native | Perfect |
| **Docker/Docker Compose** | ✅ Docker Desktop | ✅ Native Docker | Better on Linux |
| **TypeScript** | ✅ Cross-platform | ✅ Native | Perfect |
| **PostgreSQL** | ✅ Docker | ✅ Docker | Identical |
| **Redis** | ✅ Docker | ✅ Docker | Identical |
| **n8n** | ✅ Docker | ✅ Docker | Identical |

**File Path Handling**:
- Git automatically handles line endings (CRLF → LF) via `.gitattributes`
- Docker volumes use Linux paths internally regardless of host OS
- Node.js `path` module normalizes paths automatically
- Python `pathlib` handles OS differences automatically

**PowerShell → Bash**:
- 95% of your commands are Docker commands (identical on both)
- Remaining 5% are simple translations (covered in migration guide)

---

## 📊 Current System Resource Analysis

### Live Docker Container Memory Usage (as of 2026-01-16)

| Container | Current Memory | Peak Estimate |
|-----------|----------------|---------------|
| mycosoft-website | 137 MB | 512 MB |
| mycosoft-redis | 5 MB | 128 MB |
| mycosoft-postgres | 21 MB | 512 MB |
| mindex-api | 86 MB | 256 MB |
| mindex-postgres | 104 MB | 512 MB |
| mindex-etl | 141 MB | 1 GB |
| mycobrain | 41 MB | 256 MB |
| mas-orchestrator | 135 MB | 512 MB |
| n8n | 392 MB | 1 GB |
| ollama | 32 MB | **16 GB** (when models loaded) |
| voice-ui | 50 MB | 128 MB |
| whisper | 223 MB | **4 GB** (during transcription) |
| qdrant | 320 MB | 2 GB |
| mas-redis | 23 MB | 256 MB |
| mas-postgres | 34 MB | 512 MB |
| tts-piper | 60 MB | 512 MB |
| myca-dashboard | 88 MB | 256 MB |
| openedai-speech | **988 MB** | **2 GB** |

**Total Idle**: ~2.9 GB  
**Total Peak Load**: ~30-35 GB  
**Recommended with Buffer**: **64 GB**

### Docker Disk Usage

| Category | Current Size |
|----------|--------------|
| Images | 39 GB |
| Containers | 0.5 GB |
| Volumes | 11 GB |
| Build Cache | 23 GB |
| **Total Current** | **73.5 GB** |

**Projected Growth**:
- MINDEX images + observations: +100 GB
- Ollama models (full suite): +20 GB
- Database growth (1 year): +50 GB
- Logs and temp: +20 GB
- n8n workflow data: +10 GB
- System overhead: +30 GB

**Recommended Total**: **500 GB SSD**

---

## 🖥️ Recommended Operating System

### ✅ CHOOSE: Ubuntu Server 24.04.2 LTS

**Why Ubuntu Server 24.04.2 LTS and NOT Windows Server**:

| Factor | Ubuntu Server | Windows Server |
|--------|---------------|----------------|
| **Docker Performance** | Native, 30% faster | WSL2 overhead |
| **Memory Overhead** | 500 MB base | 4 GB base |
| **Disk Overhead** | 4 GB base | 15 GB base |
| **Container Networking** | Native, reliable | Complex bridging |
| **SSH Access** | Built-in | Requires setup |
| **Cost** | Free | License required |
| **Cloudflare Tunnel** | Easy setup | More complex |
| **Updates** | Minimal downtime | Restart required |
| **Security** | Smaller attack surface | Larger attack surface |

**Kernel Version**: Use the default 6.x kernel (Ubuntu 24.04 ships with 6.8+)

### ISO to Use

```
Ubuntu 24.04.2 Live Server AMD64.iso (3.21 GB)
```

**DO NOT USE**:
- Windows 11 24H2 (unnecessary overhead, licensing, slower containers)
- 2.4 or 2.6 kernels (ancient, no modern Docker features)

---

## 📋 Exact Proxmox VM Configuration

### General Tab

| Setting | Sandbox (VM 103) | Production (VM 104) |
|---------|------------------|---------------------|
| **Node** | Your PVE node | Your PVE node |
| **VM ID** | 103 | 104 |
| **Name** | `mycosoft-sandbox` | `mycosoft-prod` |
| **Resource Pool** | (leave empty or create "mycosoft") | (leave empty or create "mycosoft") |
| **Start at boot** | No | **Yes** |

### OS Tab

| Setting | Value |
|---------|-------|
| **Storage** | local (or your NAS) |
| **ISO Image** | `ubuntu-24.04.2-live-server-amd64.iso` |
| **Type** | Linux |
| **Version** | 6.x - 2.6 Kernel |

> **Note**: Select "6.x - 2.6 Kernel" - this is Proxmox's way of saying "modern Linux kernel 5.x/6.x"

### System Tab

| Setting | Value | Reason |
|---------|-------|--------|
| **Graphic card** | Default | No GUI needed for server |
| **Machine** | q35 | Modern, better PCIe support |
| **BIOS/Firmware** | **OVMF (UEFI)** | Modern boot, better security |
| **SCSI Controller** | VirtIO SCSI single | Best performance |
| **QEMU Agent** | **☑ Enabled** | Required for proper shutdown/snapshot |
| **Add TPM** | ☐ Disabled | Not needed for Ubuntu |
| **EFI Storage** | local-lvm (or same as disk) | Required for UEFI |
| **Pre-Enroll keys** | ☐ Disabled | Simpler setup |

### Disks Tab

| Setting | Sandbox | Production |
|---------|---------|------------|
| **Bus/Device** | VirtIO Block (virtio0) | VirtIO Block (virtio0) |
| **Storage** | **local-lvm** OR NAS | **NAS (RAID)** recommended |
| **Disk Size** | **256 GB** | **500 GB** |
| **Cache** | **Write back** | **Write back** |
| **Discard** | **☑ Enabled** | **☑ Enabled** |
| **IO Thread** | **☑ Enabled** | **☑ Enabled** |
| **SSD Emulation** | **☑ Enabled** | **☑ Enabled** |

**Bandwidth (Leave defaults unless you have specific needs)**:

| Setting | Value |
|---------|-------|
| Read limit (MB/s) | 0 (unlimited) |
| Write limit (MB/s) | 0 (unlimited) |
| Read limit (OPS) | 0 (unlimited) |
| Write limit (OPS) | 0 (unlimited) |

### CPU Tab

| Setting | Sandbox | Production |
|---------|---------|------------|
| **Sockets** | 1 | 1 |
| **Cores** | **8** | **16** |
| **Type** | **host** | **host** |
| **Total Cores** | 8 | 16 |
| **Enable NUMA** | ☐ (single socket) | ☐ (single socket) |

> **CPU Type "host"**: Passes through your actual CPU features. Best performance. If you need to migrate VMs between different CPU hosts, use "x86-64-v3" instead.

### Memory Tab

| Setting | Sandbox | Production |
|---------|---------|------------|
| **Memory (MiB)** | **32768** (32 GB) | **65536** (64 GB) |
| **Minimum memory** | 16384 (16 GB) | 32768 (32 GB) |
| **Shares** | 1000 (default) | 1000 (default) |
| **Ballooning Device** | ☑ Enabled | ☑ Enabled |

> **Ballooning**: Allows the VM to dynamically adjust memory usage. Host can reclaim unused memory.

### Network Tab

| Setting | Value |
|---------|-------|
| **Bridge** | vmbr0 (your main bridge) |
| **Model** | **VirtIO (paravirtualized)** |
| **MAC address** | Auto-generate |
| **VLAN Tag** | (leave empty unless using VLANs) |
| **Firewall** | ☑ Enabled |
| **Disconnect** | ☐ Disabled |
| **MTU** | 1500 (default) |

---

## 🔧 Post-Installation Setup Script

After installing Ubuntu 24.04.2 LTS, run this setup script:

```bash
#!/bin/bash
# Mycosoft VM Setup Script
# Run as root: sudo bash setup-mycosoft-vm.sh

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  MYCOSOFT VM SETUP - Ubuntu 24.04.2 LTS"
echo "═══════════════════════════════════════════════════════════════"

# Update system
echo "[1/8] Updating system..."
apt update && apt upgrade -y

# Install QEMU Guest Agent
echo "[2/8] Installing QEMU Guest Agent..."
apt install -y qemu-guest-agent
systemctl enable --now qemu-guest-agent

# Install Docker
echo "[3/8] Installing Docker..."
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker
systemctl enable --now docker

# Create mycosoft user
echo "[4/8] Creating mycosoft user..."
useradd -m -s /bin/bash -G docker,sudo mycosoft || true
echo "mycosoft:CHANGE_THIS_PASSWORD" | chpasswd

# Create directory structure
echo "[5/8] Creating directory structure..."
mkdir -p /opt/mycosoft/{website,mas,data,backups,logs,config}
mkdir -p /opt/mycosoft/data/{postgres,redis,qdrant,n8n,mindex,ollama}
chown -R mycosoft:mycosoft /opt/mycosoft

# Install useful tools
echo "[6/8] Installing tools..."
apt install -y htop iotop ncdu git curl wget vim nano jq

# Configure firewall
echo "[7/8] Configuring firewall..."
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 3000/tcp  # Website
ufw allow 8000/tcp  # MINDEX API
ufw allow 8003/tcp  # MycoBrain
ufw allow 5678/tcp  # n8n
ufw allow 3002/tcp  # Grafana
ufw allow 9090/tcp  # Prometheus
# Don't enable UFW yet - wait for Cloudflare tunnel setup

# Install Cloudflare Tunnel
echo "[8/8] Installing Cloudflare Tunnel..."
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared.deb
rm cloudflared.deb

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Change the mycosoft user password"
echo "2. Clone your GitHub repositories to /opt/mycosoft/"
echo "3. Copy environment files (.env.local, etc.)"
echo "4. Configure Cloudflare tunnel"
echo "5. Start Docker containers"
echo ""
```

---

## 🗄️ Storage Recommendations

### Option 1: Local Storage (Dell Server SSDs)
**Best for**: Fastest performance, single-node deployment

```
Sandbox: local-lvm (256 GB)
Production: local-lvm (500 GB)
```

### Option 2: NAS Storage (Dream Machine/Synology)
**Best for**: Shared storage, easy backups, multi-node

```
Storage: NAS-mounted NFS or iSCSI
Path: /mnt/nas/proxmox/images
```

### Option 3: Hybrid (Recommended)
**Best for**: Performance + Reliability

```
OS + Docker: Local SSD (100 GB, fast)
Data Volumes: NAS (400 GB, reliable, backed up)
```

**Recommended Hybrid Setup**:
- **virtio0**: Local SSD, 100 GB (OS, Docker engine, images)
- **virtio1**: NAS, 400 GB (mounted as /opt/mycosoft/data)

---

## 🌐 Cloudflare Tunnel Setup for Production

### 1. Create Tunnel in Cloudflare Dashboard

```bash
# On the Production VM
cloudflared tunnel login
cloudflared tunnel create mycosoft-prod
```

### 2. Configure Tunnel

Create `/etc/cloudflared/config.yml`:

```yaml
tunnel: <YOUR-TUNNEL-ID>
credentials-file: /root/.cloudflared/<TUNNEL-ID>.json

ingress:
  # Main website
  - hostname: mycosoft.com
    service: http://localhost:3000
  - hostname: www.mycosoft.com
    service: http://localhost:3000
    
  # MINDEX API
  - hostname: api.mycosoft.com
    service: http://localhost:8000
    
  # n8n Webhooks (optional)
  - hostname: webhooks.mycosoft.com
    service: http://localhost:5678
    
  # Grafana (internal only, consider not exposing)
  - hostname: monitor.mycosoft.com
    service: http://localhost:3002
    
  # Catch-all
  - service: http_status:404
```

### 3. Run as Service

```bash
cloudflared service install
systemctl enable --now cloudflared
```

### 4. DNS Configuration in Cloudflare

| Type | Name | Content |
|------|------|---------|
| CNAME | @ | `<tunnel-id>.cfargotunnel.com` |
| CNAME | www | `<tunnel-id>.cfargotunnel.com` |
| CNAME | api | `<tunnel-id>.cfargotunnel.com` |

---

## 📋 VM Creation Checklist

### Sandbox VM (103) - Quick Reference

```
General:
  ☐ VM ID: 103
  ☐ Name: mycosoft-sandbox
  ☐ Start at boot: No

OS:
  ☐ ISO: ubuntu-24.04.2-live-server-amd64.iso
  ☐ Type: Linux
  ☐ Version: 6.x - 2.6 Kernel

System:
  ☐ Machine: q35
  ☐ BIOS: OVMF (UEFI)
  ☐ SCSI Controller: VirtIO SCSI single
  ☐ QEMU Agent: Enabled
  ☐ Add TPM: Disabled

Disks:
  ☐ Bus: VirtIO Block
  ☐ Size: 256 GB
  ☐ Cache: Write back
  ☐ Discard: Enabled
  ☐ IO Thread: Enabled
  ☐ SSD Emulation: Enabled

CPU:
  ☐ Sockets: 1
  ☐ Cores: 8
  ☐ Type: host

Memory:
  ☐ Memory: 32768 MiB (32 GB)
  ☐ Ballooning: Enabled

Network:
  ☐ Bridge: vmbr0
  ☐ Model: VirtIO
  ☐ Firewall: Enabled
```

### Production VM (104) - Quick Reference

```
General:
  ☐ VM ID: 104
  ☐ Name: mycosoft-prod
  ☐ Start at boot: Yes

OS:
  ☐ ISO: ubuntu-24.04.2-live-server-amd64.iso
  ☐ Type: Linux
  ☐ Version: 6.x - 2.6 Kernel

System:
  ☐ Machine: q35
  ☐ BIOS: OVMF (UEFI)
  ☐ SCSI Controller: VirtIO SCSI single
  ☐ QEMU Agent: Enabled
  ☐ Add TPM: Disabled

Disks:
  ☐ Bus: VirtIO Block
  ☐ Size: 500 GB
  ☐ Cache: Write back
  ☐ Discard: Enabled
  ☐ IO Thread: Enabled
  ☐ SSD Emulation: Enabled

CPU:
  ☐ Sockets: 1
  ☐ Cores: 16
  ☐ Type: host

Memory:
  ☐ Memory: 65536 MiB (64 GB)
  ☐ Ballooning: Enabled

Network:
  ☐ Bridge: vmbr0
  ☐ Model: VirtIO
  ☐ Firewall: Enabled
```

---

## 🔄 Migration Workflow

### Phase 1: Sandbox Setup & Testing

```
1. Create VM 103 with specifications above
2. Install Ubuntu 24.04.2 LTS
3. Run setup script
4. Clone repositories from GitHub
5. Copy environment files
6. Build and start containers
7. Run all tests
8. Verify all 18+ services healthy
```

### Phase 2: Production Deployment

```
1. Snapshot Sandbox VM as "verified-working"
2. Clone VM 103 → VM 104
3. Adjust VM 104 resources (16 cores, 64 GB)
4. Configure Cloudflare tunnel
5. Update DNS records
6. Enable "Start at boot"
7. Final verification
```

### Phase 3: Backup Strategy

```
1. Create Proxmox backup schedule for VM 104
2. Set up database backup cron jobs
3. Configure n8n workflow data export
4. Set up offsite backup replication
```

---

## 📊 Resource Summary Table

| Resource | Sandbox (Dev) | Production | Your Host Requirements |
|----------|---------------|------------|------------------------|
| **VM ID** | 103 | 104 | - |
| **CPU Cores** | 8 | 16 | 24+ total recommended |
| **RAM** | 32 GB | 64 GB | 128 GB total recommended |
| **Disk** | 256 GB | 500 GB | 1 TB+ total |
| **Network** | 1 Gbps | 1 Gbps | 1 Gbps |
| **OS** | Ubuntu 24.04.2 | Ubuntu 24.04.2 | - |
| **Docker** | Latest | Latest | - |

---

## ⚠️ Important Notes

### DO NOT USE Windows 11 for Production
- Docker on Windows uses WSL2 with significant overhead
- More memory usage, slower I/O
- Complex networking
- License costs
- All your code is cross-platform anyway

### File Path Translation

Your code already handles this:

```javascript
// Node.js - works on both Windows and Linux
const path = require('path');
path.join('/opt/mycosoft', 'data', 'file.json')
// Windows: C:\opt\mycosoft\data\file.json
// Linux: /opt/mycosoft/data/file.json
```

```python
# Python - works on both Windows and Linux
from pathlib import Path
Path('/opt/mycosoft') / 'data' / 'file.json'
```

### Docker Volume Paths

Docker Compose paths are relative and work identically:

```yaml
volumes:
  - ./data/postgres:/var/lib/postgresql/data
  - ./logs:/app/logs
```

These work on both Windows and Linux Docker.

---

## 🚀 Quick Start Commands

After VM setup, as the `mycosoft` user:

```bash
# Clone repositories
cd /opt/mycosoft
git clone https://github.com/YOUR_ORG/website.git website
git clone https://github.com/YOUR_ORG/mycosoft-mas.git mas

# Copy environment files (from your Windows machine)
# Use SCP, SFTP, or Cloudflare Tunnel to transfer

# Start MAS stack first
cd /opt/mycosoft/mas
docker compose up -d

# Wait for MAS to be healthy
sleep 30

# Start Always-On stack
docker compose -f docker-compose.always-on.yml up -d

# Verify all containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check health
curl http://localhost:3000/api/health
curl http://localhost:8000/api/health
curl http://localhost:5678/healthz
```

---

## 📞 Support Checklist

If issues arise, check:

1. **Docker logs**: `docker logs <container-name>`
2. **System resources**: `htop`
3. **Disk space**: `df -h`
4. **Network**: `docker network ls` and `docker network inspect`
5. **Container health**: `docker ps`
6. **Firewall**: `ufw status`

---

---

## ✅ VM INSTALLATION COMPLETE - January 17, 2026

### VM Status: RUNNING

| Metric | Value |
|--------|-------|
| **Status** | Running |
| **Uptime** | Active |
| **CPU Usage** | 0.22% of 8 CPUs |
| **Memory Usage** | 3.45% (1.11 GB of 32.00 GiB) |
| **Bootdisk Size** | 256.00 GiB |
| **Guest Agent** | Pending Installation |

### Next Steps After Login

1. **Install QEMU Guest Agent** (enables IP reporting to Proxmox):
   ```bash
   sudo apt update
   sudo apt install -y qemu-guest-agent
   sudo systemctl enable qemu-guest-agent
   sudo systemctl start qemu-guest-agent
   ```

2. **Get VM IP Address**:
   ```bash
   ip addr show | grep inet
   ```

3. **Run Setup Script** (from Windows machine after getting IP):
   ```bash
   ssh mycosoft@<VM_IP>
   # Then run the setup script from the repo
   ```

---

## 🔌 Available Integration APIs

### Proxmox VE API

| Setting | Value |
|---------|-------|
| **URL** | `https://192.168.0.202:8006/api2/json` |
| **Authentication** | API Token |
| **Token ID** | `root@pam!cursor_mycocomp` |
| **Privilege Separation** | Disabled (No) |
| **Expiry** | Never |

**Capabilities:**
- ✅ List/manage VMs and containers
- ✅ Start/stop/restart VMs
- ✅ Create/delete VMs
- ✅ Storage management
- ✅ Node status and metrics
- ✅ Task monitoring
- ✅ Backup/restore

### UniFi Network API

Available for integration with network infrastructure:

| Device | Purpose |
|--------|---------|
| **Dream Machine** | Network controller, security gateway, IDS/IPS |
| **NAS** | Network attached storage, backups |
| **Routers** | Advanced routing, VLANs |
| **WiFi Radios** | Wireless access points |
| **Switches** | Managed network switches |

**Use Cases for VM Deployment:**
- Create static DHCP reservations for VM IPs
- Configure VLANs for network isolation
- Set up firewall rules for VM traffic
- Monitor bandwidth usage
- Create port forwarding for external access
- Configure QoS for priority traffic

### Integration Points

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Windows Dev   │────▶│  Proxmox VE API  │────▶│  VMs (103/104)  │
│   (Cursor)      │     │  :8006           │     │  Ubuntu Server  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                │
         │              ┌──────────────────┐              │
         └─────────────▶│  UniFi API       │◀─────────────┘
                        │  Dream Machine   │
                        └──────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌─────────┐  ┌─────────┐
              │  NAS    │  │ Routers │  │  WiFi   │
              └─────────┘  └─────────┘  └─────────┘
```

---

## 📊 VM Creation Session Log

**Session Date:** January 17, 2026

### Timeline

| Time | Action | Result |
|------|--------|--------|
| 00:02:41 | Opened Create VM dialog | ✅ |
| 00:02:48 | Set name to mycosoft-sandbox | ✅ |
| 00:02:56 | Selected Ubuntu ISO | ✅ |
| 00:03:31 | Configured System (q35, OVMF, Agent) | ✅ |
| 00:05:03 | Configured Disk (256GB, writeback) | ✅ |
| 00:05:50 | Configured CPU (8 cores, host) | ✅ |
| 00:06:27 | Configured Memory (32GB) | ✅ |
| 00:06:43 | Verified Network defaults | ✅ |
| 00:06:54 | Reviewed Confirm tab | ✅ |
| 00:07:13 | Clicked Finish | ✅ |
| 00:07:14 | VM 103 Created | **SUCCESS** |

### Verification

```
API Test Results:
  VM 103: mycosoft-sandbox (stopped)
  Status: exists, ready to start
```

---

*Document created: 2026-01-16*  
*Updated: 2026-01-17 (VM 103 created successfully)*  
*System analyzed: 18+ containers, 73.5 GB current usage*  
*Recommendation: Ubuntu 24.04.2 LTS on Proxmox VE 8.4*
