# Proxmox & UniFi API Reference

*Created: January 17, 2026*

Quick reference for all available infrastructure APIs.

---

## 🖥️ Proxmox VE API

### Connection Details

| Setting | Value |
|---------|-------|
| **Host** | `192.168.0.202` |
| **Port** | `8006` |
| **Protocol** | HTTPS (self-signed cert, verify=False) |
| **Base URL** | `https://192.168.0.202:8006/api2/json` |

### Authentication

```python
# API Token Authentication
headers = {
    "Authorization": "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
}
```

| Token Setting | Value |
|---------------|-------|
| **User** | `root@pam` |
| **Token ID** | `cursor_agent` |
| **Secret** | `bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e` |
| **Full Token** | `root@pam!cursor_agent` |
| **Privilege Separation** | Disabled (No) |
| **Expiry** | Never |
| **Updated** | January 23, 2026 |

### Common Endpoints

#### Get Nodes
```http
GET /api2/json/nodes
```

#### Get VMs on Node
```http
GET /api2/json/nodes/{node}/qemu
```

#### Get VM Status
```http
GET /api2/json/nodes/{node}/qemu/{vmid}/status/current
```

#### Start VM
```http
POST /api2/json/nodes/{node}/qemu/{vmid}/status/start
```

#### Stop VM
```http
POST /api2/json/nodes/{node}/qemu/{vmid}/status/stop
```

#### Get Storage
```http
GET /api2/json/nodes/{node}/storage
GET /api2/json/storage
```

#### Get ISO Content
```http
GET /api2/json/nodes/{node}/storage/{storage}/content
```

### Python Example

```python
import requests
import urllib3
urllib3.disable_warnings()

PROXMOX_URL = "https://192.168.0.202:8006/api2/json"
HEADERS = {
    "Authorization": "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
}

def get_vms():
    response = requests.get(
        f"{PROXMOX_URL}/nodes/pve/qemu",
        headers=HEADERS,
        verify=False
    )
    return response.json()["data"]

def start_vm(vmid):
    response = requests.post(
        f"{PROXMOX_URL}/nodes/pve/qemu/{vmid}/status/start",
        headers=HEADERS,
        verify=False
    )
    return response.json()
```

### Current Infrastructure

| VM ID | Name | Purpose | Status |
|-------|------|---------|--------|
| 100 | VM 100 | Unknown | Running |
| 101 | ubuntu-cursor | Development | Stopped |
| 102 | WIN11-TEMPLATE | Windows Template | Stopped |
| **103** | **mycosoft-sandbox** | **Mycosoft Sandbox** | **Created** |
| 104 | mycosoft-prod | Production (planned) | Not created |

### Server Specifications

| Resource | Value |
|----------|-------|
| **Node** | pve |
| **CPU** | 24 cores (Intel Xeon X5670 @ 2.93GHz) |
| **RAM** | 118 GB total |
| **Local Storage** | 93.9 GB (ISOs, backups) |
| **LVM Storage** | 5.43 TB (VM disks) |

---

## 🌐 UniFi Network API

### Available Devices

| Device Type | Purpose | Integration Use |
|-------------|---------|-----------------|
| **Dream Machine** | Network controller, router, security gateway | Central API endpoint |
| **NAS** | Network attached storage | VM backups, file shares |
| **Routers** | L3 routing, VLANs | VM network isolation |
| **WiFi Radios** | Wireless access points | IoT/MycoBrain connectivity |
| **Switches** | Managed L2 switches | Port VLANs, PoE |

### API Capabilities

- **Network Management**
  - Create/manage VLANs
  - Configure firewall rules
  - Set up port forwarding
  - Manage DHCP reservations

- **Monitoring**
  - Client device tracking
  - Bandwidth statistics
  - Connection health
  - Latency metrics

- **Automation**
  - Static IP assignments for VMs
  - QoS policies
  - Traffic shaping
  - IDS/IPS rules

### Integration with Proxmox VMs

```
┌────────────────────────────────────────────────────────────┐
│                     UniFi Network                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Dream Mach. │  │   Routers   │  │   Switches  │        │
│  │  (Gateway)  │  │  (VLANs)    │  │   (Ports)   │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          │                                  │
│                    ┌─────┴─────┐                           │
│                    │  vmbr0    │  Bridge                   │
│                    └─────┬─────┘                           │
└──────────────────────────┼─────────────────────────────────┘
                           │
┌──────────────────────────┼─────────────────────────────────┐
│                    Proxmox VE                              │
│         ┌────────────────┼────────────────┐                │
│         │                │                │                │
│    ┌────┴────┐     ┌────┴────┐     ┌────┴────┐           │
│    │ VM 103  │     │ VM 104  │     │ VM 100  │           │
│    │ Sandbox │     │  Prod   │     │ Other   │           │
│    └─────────┘     └─────────┘     └─────────┘           │
└────────────────────────────────────────────────────────────┘
```

### Recommended VM Network Setup

1. **DHCP Reservation** for consistent IPs
2. **VLAN 10** for production traffic
3. **VLAN 20** for sandbox/dev traffic
4. **Firewall Rules** to isolate environments
5. **QoS** for prioritizing production

---

## 📁 Related Documentation

| Document | Path | Description |
|----------|------|-------------|
| VM Specifications | `docs/PROXMOX_VM_SPECIFICATIONS.md` | Full VM specs and setup |
| Creation Session | `docs/SESSION_VM_CREATION_JAN17_2026.md` | Step-by-step creation log |
| API Test Script | `scripts/test_proxmox_api.py` | Python API testing |
| Deployment Guide | `docs/COMPLETE_VM_DEPLOYMENT_GUIDE.md` | Full deployment process |

---

## 🔧 Quick Commands

### Test API Connectivity
```powershell
python scripts\test_proxmox_api.py
```

### List VMs via curl (from Linux/Windows)
```bash
curl -k -H "Authorization: PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e" \
     https://192.168.0.202:8006/api2/json/nodes/pve/qemu
```

### Access Web UI
```
URL: https://192.168.0.202:8006
User: root
Password: 20202020
```
