# Ubiquiti Network Integration Guide

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **Prerequisites**: UniFi OS access, UDM Pro admin credentials

This document covers the complete setup of the Ubiquiti Dream Machine Pro as the network backbone for the MYCA infrastructure, including NAS storage configuration, VLAN setup, and API integration.

---

## Table of Contents

1. [UDM Pro Overview](#udm-pro-overview)
2. [26TB NAS Storage Setup](#26tb-nas-storage-setup)
3. [VLAN Configuration](#vlan-configuration)
4. [Firewall Rules](#firewall-rules)
5. [Static IP Assignments](#static-ip-assignments)
6. [DNS Configuration](#dns-configuration)
7. [Cloudflared Installation](#cloudflared-installation)
8. [UniFi API Integration](#unifi-api-integration)
9. [Troubleshooting](#troubleshooting)

---

## UDM Pro Overview

### Device Specifications

| Property | Value |
|----------|-------|
| **Model** | UniFi Dream Machine Pro |
| **IP Address** | 192.168.0.1 |
| **Role** | Gateway, Router, NAS Host, Cloudflare Tunnel Endpoint |
| **Storage** | 26TB (Internal HDDs) |
| **UniFi OS Version** | 3.x+ |

### Network Interfaces

| Port | Connection | Purpose |
|------|------------|---------|
| WAN | ISP Fiber | Internet uplink |
| LAN 1 | Core Switch | Main network |
| LAN 2 | IoT Switch | VLAN 40 |
| SFP+ | (Reserved) | Future 10Gbe |

---

## 26TB NAS Storage Setup

### Step 1: Enable Storage in UniFi OS

1. Access UniFi OS at `https://192.168.0.1`
2. Navigate to **Console Settings** > **Storage**
3. Initialize the storage array with the 26TB drives
4. Wait for initialization to complete (may take several hours)

### Step 2: Create SMB Share for MYCA

1. Go to **Console Settings** > **Storage** > **Shares**
2. Create a new share:

| Setting | Value |
|---------|-------|
| **Name** | mycosoft |
| **Path** | /mycosoft |
| **Protocol** | SMB (Windows Compatible) |
| **Access** | Authenticated Users |

3. Create a dedicated user for MYCA access:

| Setting | Value |
|---------|-------|
| **Username** | myca-service |
| **Password** | (Generate strong password, store in Vault) |
| **Access Level** | Read/Write |

### Step 3: Create NFS Share for Linux VMs

1. Create an additional NFS share for Proxmox VMs:

| Setting | Value |
|---------|-------|
| **Name** | mycosoft-nfs |
| **Path** | /mycosoft |
| **Protocol** | NFS v4 |
| **Allowed Hosts** | 192.168.20.0/24, 192.168.30.0/24 |
| **Root Squash** | Enabled |

### Step 4: Directory Structure

Create the following directory structure on the NAS:

```
/mycosoft/
├── databases/
│   ├── postgres/          # PostgreSQL data
│   ├── redis/             # Redis persistence
│   └── qdrant/            # Qdrant vector store
├── knowledge/
│   ├── embeddings/        # Vector embeddings
│   └── documents/         # Document store
├── agents/
│   ├── cycles/            # Agent cycle data
│   ├── insights/          # Agent insights
│   ├── workloads/         # Active workloads
│   └── wisdom/            # Accumulated knowledge
├── website/
│   ├── static/            # Static assets
│   └── uploads/           # User uploads
├── backups/
│   ├── daily/             # Daily backups
│   ├── weekly/            # Weekly backups
│   └── monthly/           # Monthly backups
├── audit/
│   └── logs/              # Audit trail logs
├── dev/
│   ├── data/              # Development data
│   └── logs/              # Development logs
└── shared/
    ├── models/            # AI models
    └── configs/           # Shared configurations
```

### Step 5: Mount on Windows (mycocomp)

Use the provided PowerShell script:

```powershell
# Mount NAS as M: drive
.\scripts\mount_nas.ps1 -DriveLetter M -NASAddress 192.168.0.1 -ShareName mycosoft

# Verify the mount
.\scripts\verify_storage.ps1
```

**Manual mount command:**

```powershell
# Create persistent network drive
net use M: \\192.168.0.1\mycosoft /user:myca-service <password> /persistent:yes

# Set environment variable
[Environment]::SetEnvironmentVariable("NAS_STORAGE_PATH", "M:\", "User")
```

### Step 6: Mount on Linux VMs (NFS)

On each production VM, add to `/etc/fstab`:

```bash
# MYCA NAS mount
192.168.0.1:/mycosoft /mnt/mycosoft nfs4 defaults,_netdev,noatime 0 0
```

Mount immediately:

```bash
sudo mkdir -p /mnt/mycosoft
sudo mount -a
```

---

## VLAN Configuration

### VLAN Overview

| VLAN ID | Name | Subnet | DHCP Range | Purpose |
|---------|------|--------|------------|---------|
| 1 | Default | 192.168.0.0/24 | .100-.199 | Management, Development |
| 20 | Production | 192.168.20.0/24 | Disabled | Production VMs |
| 30 | Agents | 192.168.30.0/24 | .10-.99 | Agent VMs |
| 40 | IoT | 192.168.40.0/24 | .10-.99 | MycoBrain Devices |

### Step 1: Create VLANs in UniFi

1. Access UniFi Network Controller at `https://192.168.0.1:443`
2. Navigate to **Settings** > **Networks**
3. Create each VLAN:

**VLAN 20 - Production:**
```
Name: Production
VLAN ID: 20
Gateway IP: 192.168.20.1/24
DHCP Mode: None (static IPs only)
Domain Name: prod.myca.local
```

**VLAN 30 - Agents:**
```
Name: Agents
VLAN ID: 30
Gateway IP: 192.168.30.1/24
DHCP Mode: DHCP Server
DHCP Range: 192.168.30.10 - 192.168.30.99
Domain Name: agents.myca.local
```

**VLAN 40 - IoT:**
```
Name: IoT
VLAN ID: 40
Gateway IP: 192.168.40.1/24
DHCP Mode: DHCP Server
DHCP Range: 192.168.40.10 - 192.168.40.99
Domain Name: iot.myca.local
Isolation: Enabled (IoT quarantine)
```

### Step 2: Assign VLANs to Ports

Configure switch ports for VLAN assignment:

| Port | Profile | Purpose |
|------|---------|---------|
| Proxmox Uplinks | All (Trunk) | All VLANs tagged |
| mycocomp | Default | Untagged VLAN 1 |
| IoT Switch | IoT | Untagged VLAN 40 |

---

## Firewall Rules

### Traffic Flow Matrix

| Source | Destination | Allow | Notes |
|--------|-------------|-------|-------|
| VLAN 1 | VLAN 20 | Yes | Admin access |
| VLAN 1 | VLAN 30 | Yes | Management |
| VLAN 1 | VLAN 40 | Yes | IoT management |
| VLAN 20 | VLAN 1 | No | Security boundary |
| VLAN 20 | VLAN 30 | Yes | Agent control |
| VLAN 20 | VLAN 40 | Yes | Sensor data |
| VLAN 30 | VLAN 20 | Limited | API ports only |
| VLAN 40 | VLAN 20 | Limited | Data ports only |

### Step 1: Create Firewall Rules

Navigate to **Settings** > **Firewall & Security** > **Firewall Rules**

**Rule 1: Allow Management to Production**
```
Name: Mgmt-to-Prod
Type: LAN In
Action: Accept
Source: VLAN 1
Destination: VLAN 20
Port: Any
```

**Rule 2: Block Production to Management**
```
Name: Block-Prod-to-Mgmt
Type: LAN In
Action: Drop
Source: VLAN 20
Destination: VLAN 1
Port: Any
```

**Rule 3: Agents to Production API Only**
```
Name: Agents-to-Prod-API
Type: LAN In
Action: Accept
Source: VLAN 30
Destination: VLAN 20 (192.168.20.10)
Port: 8001, 8000, 6379, 5432
```

**Rule 4: IoT to Production Data**
```
Name: IoT-to-Prod-Data
Type: LAN In
Action: Accept
Source: VLAN 40
Destination: VLAN 20 (192.168.20.10)
Port: 8001, 1883 (MQTT)
```

**Rule 5: Block IoT to All Others**
```
Name: IoT-Isolation
Type: LAN In
Action: Drop
Source: VLAN 40
Destination: RFC1918
Port: Any
```

### Step 2: Enable Threat Management

1. Navigate to **Settings** > **Firewall & Security** > **Threat Management**
2. Enable IDS/IPS with recommended settings
3. Configure alerts for:
   - Port scans
   - Unusual traffic patterns
   - Known threat signatures

---

## Static IP Assignments

### VLAN 1 - Management

| IP | MAC (if known) | Device | Description |
|----|----------------|--------|-------------|
| 192.168.0.1 | UDM Pro | Gateway | Network controller |
| 192.168.0.2 | - | DC1 | Proxmox Node |
| 192.168.0.131 | - | DC2 | Proxmox Node |
| 192.168.0.202 | - | Build | Primary Proxmox |

### VLAN 20 - Production

Configure in UniFi or via Proxmox cloud-init:

| IP | VM | Description |
|----|-----|-------------|
| 192.168.20.10 | myca-core | MYCA Orchestrator |
| 192.168.20.11 | myca-website | Website VM |
| 192.168.20.12 | myca-database | Database VM |

### Configure in UniFi

1. Navigate to **Client Devices**
2. Select the device
3. Click **Settings** (gear icon)
4. Set **Fixed IP Address**
5. Save

---

## DNS Configuration

### Local DNS Entries

Add to UniFi DNS settings (**Settings** > **Networks** > **Global Network Settings** > **DNS**):

| Hostname | IP Address |
|----------|------------|
| nas.myca.local | 192.168.0.1 |
| myca-core.myca.local | 192.168.20.10 |
| myca-website.myca.local | 192.168.20.11 |
| myca-database.myca.local | 192.168.20.12 |
| build.myca.local | 192.168.0.202 |
| dc1.myca.local | 192.168.0.2 |
| dc2.myca.local | 192.168.0.131 |

### External DNS (Cloudflare)

Configured via Cloudflare Dashboard:

| Record | Type | Value |
|--------|------|-------|
| mycosoft.com | CNAME | tunnel-uuid.cfargotunnel.com |
| www | CNAME | mycosoft.com |
| api | CNAME | tunnel-uuid.cfargotunnel.com |
| dashboard | CNAME | tunnel-uuid.cfargotunnel.com |
| webhooks | CNAME | tunnel-uuid.cfargotunnel.com |

---

## Cloudflared Installation

### Option A: Docker on UDM Pro

SSH into UDM Pro and install cloudflared:

```bash
# SSH to UDM Pro
ssh root@192.168.0.1

# Install cloudflared via Docker
podman run -d \
  --name cloudflared \
  --restart always \
  -v /mnt/data/cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest \
  tunnel --config /etc/cloudflared/config.yml run

# Verify running
podman ps | grep cloudflared
```

### Option B: Run on myca-core VM (Recommended)

Install on the production VM for easier management:

```bash
# On myca-core VM
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create mycosoft-tunnel

# Copy config
sudo cp /path/to/config.yml /etc/cloudflared/config.yml
sudo cp credentials.json /etc/cloudflared/

# Install as service
sudo cloudflared service install

# Enable and start
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### Configuration File

Use the existing config at `config/cloudflared/config.yml`:

```yaml
tunnel: mycosoft-tunnel
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: mycosoft.com
    service: http://localhost:3000
  - hostname: www.mycosoft.com
    service: http://localhost:3000
  - hostname: api.mycosoft.com
    service: http://localhost:8001
  - hostname: dashboard.mycosoft.com
    service: http://localhost:3100
  - hostname: webhooks.mycosoft.com
    service: http://localhost:5678
  - service: http_status:404
```

---

## UniFi API Integration

### Enable API Access

1. Navigate to **Settings** > **System** > **Advanced**
2. Enable **Local API** if not already enabled

### API Authentication

The MYCA system uses the UniFi API client at `infra/bootstrap/unifi_client.py`.

**Environment Variables:**

```bash
UNIFI_HOST=192.168.0.1
UNIFI_PORT=443
UNIFI_USERNAME=myca-api-user
UNIFI_PASSWORD=<stored-in-vault>
UNIFI_SITE=default
```

### Create API User

1. Go to **OS Settings** > **Admins**
2. Add a new admin:

| Field | Value |
|-------|-------|
| Name | myca-api |
| Role | Limited Admin |
| Permissions | Network only (read/write) |
| 2FA | Disabled (service account) |

### Test API Connection

```python
# Test script
from infra.bootstrap.unifi_client import UniFiClient

client = UniFiClient(
    host="192.168.0.1",
    username="myca-api",
    password="<password>",
    site="default"
)

# Get client list
clients = client.get_clients()
print(f"Found {len(clients)} clients")

# Get network topology
topology = client.get_topology()
print(topology)
```

### Available API Operations

| Operation | Method | Use Case |
|-----------|--------|----------|
| `get_clients()` | GET | List connected devices |
| `get_client(mac)` | GET | Get specific device |
| `block_client(mac)` | POST | Security: block device |
| `unblock_client(mac)` | POST | Unblock device |
| `get_networks()` | GET | List VLANs |
| `get_topology()` | GET | Network visualization |

---

## Troubleshooting

### NAS Mount Issues

**Symptom**: Cannot access \\192.168.0.1\mycosoft

```powershell
# Check connectivity
Test-NetConnection -ComputerName 192.168.0.1 -Port 445

# Check credentials
net use M: \\192.168.0.1\mycosoft /user:myca-service <password>

# Clear cached credentials
net use * /delete
cmdkey /delete:192.168.0.1
```

**Linux NFS issues:**

```bash
# Check NFS connectivity
showmount -e 192.168.0.1

# Check mount
mount | grep mycosoft

# Remount
sudo umount /mnt/mycosoft
sudo mount -a
```

### VLAN Issues

**Symptom**: VMs cannot reach other VLANs

1. Check VLAN tagging on Proxmox bridges
2. Verify firewall rules in UniFi
3. Check VM network configuration:

```bash
# On VM, check IP
ip addr show

# Check routes
ip route

# Test gateway
ping 192.168.20.1
```

### Cloudflared Issues

**Symptom**: External access not working

```bash
# Check tunnel status
cloudflared tunnel info mycosoft-tunnel

# Check service status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f

# Test local endpoint
curl http://localhost:3000
```

### API Connection Issues

**Symptom**: UniFi API calls fail

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check SSL issues
client = UniFiClient(
    host="192.168.0.1",
    verify_ssl=False  # For self-signed certs
)
```

---

## Maintenance Tasks

### Daily

- [ ] Check NAS storage utilization
- [ ] Review Cloudflared tunnel status
- [ ] Monitor UniFi alerts

### Weekly

- [ ] Review firewall logs for blocked traffic
- [ ] Check VLAN connectivity
- [ ] Verify backup completion

### Monthly

- [ ] Update UniFi OS firmware
- [ ] Review API user permissions
- [ ] Audit VLAN configurations

---

## Security Considerations

1. **NAS Credentials**: Store in HashiCorp Vault, never in code
2. **API Access**: Use dedicated service account with minimal permissions
3. **Network Isolation**: Enforce VLAN boundaries via firewall rules
4. **Audit Logging**: Enable logging for all administrative actions
5. **Firmware Updates**: Keep UniFi OS updated for security patches

---

## Related Documents

- [MASTER_SETUP_GUIDE.md](./MASTER_SETUP_GUIDE.md) - Overall architecture
- [PROXMOX_VM_DEPLOYMENT.md](./PROXMOX_VM_DEPLOYMENT.md) - VM setup
- [SECURITY_HARDENING_GUIDE.md](./SECURITY_HARDENING_GUIDE.md) - Security details
- [docs/infrastructure/VLAN_SECURITY.md](../infrastructure/VLAN_SECURITY.md) - VLAN reference

---

*Document maintained by MYCA Infrastructure Team*
