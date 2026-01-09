# VLAN and Security Configuration for MYCA

This document describes the network segmentation and security configuration using UniFi.

## VLAN Architecture

| VLAN ID | Name | Subnet | Purpose |
|---------|------|--------|---------|
| 10 | Management | 192.168.10.0/24 | Network infrastructure, Proxmox management |
| 20 | Production | 192.168.20.0/24 | MYCA Core, Website, Databases |
| 30 | Agents | 192.168.30.0/24 | Agent VMs, isolated workloads |
| 40 | IoT | 192.168.40.0/24 | MycoBrain devices, sensors |
| 50 | Guest | 192.168.50.0/24 | Guest network, isolated |
| 1 | Default | 192.168.0.0/24 | Legacy devices, mycocomp development |

## Step 1: Create VLANs in UniFi

Log into UniFi Network at https://192.168.0.1

### Create VLAN 10 - Management

1. Navigate to **Settings** → **Networks**
2. Click **Create New Network**
3. Configure:
   - Name: `Management`
   - VLAN ID: `10`
   - Gateway/Subnet: `192.168.10.1/24`
   - DHCP Mode: `DHCP Server`
   - DHCP Range: `192.168.10.100 - 192.168.10.254`

### Create VLAN 20 - Production

1. Name: `Production`
2. VLAN ID: `20`
3. Gateway/Subnet: `192.168.20.1/24`
4. DHCP Range: `192.168.20.100 - 192.168.20.254`

### Create VLAN 30 - Agents

1. Name: `Agents`
2. VLAN ID: `30`
3. Gateway/Subnet: `192.168.30.1/24`
4. DHCP Range: `192.168.30.100 - 192.168.30.254`

### Create VLAN 40 - IoT

1. Name: `IoT`
2. VLAN ID: `40`
3. Gateway/Subnet: `192.168.40.1/24`
4. DHCP Range: `192.168.40.100 - 192.168.40.254`
5. Enable **IoT Isolation** if available

### Create VLAN 50 - Guest

1. Name: `Guest`
2. VLAN ID: `50`
3. Gateway/Subnet: `192.168.50.1/24`
4. DHCP Range: `192.168.50.100 - 192.168.50.254`
5. Enable **Guest Network** restrictions

## Step 2: Device Assignments

### Proxmox Nodes

Configure port profiles on switch ports connected to Proxmox:

1. Go to **Devices** → Select switch
2. Click on port connected to Proxmox node
3. Set **Port Profile** to `All` (trunk all VLANs)

### Proxmox Bridge Configuration

On each Proxmox node, configure VLAN-aware bridges:

```bash
# Edit /etc/network/interfaces
auto vmbr0
iface vmbr0 inet static
    address 192.168.0.x/24  # Management IP
    gateway 192.168.0.1
    bridge-ports enp0s25
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

### VM Network Configuration

When creating VMs, specify VLAN tag:

- MYCA Core (VM 100): `net0: virtio,bridge=vmbr0,tag=20`
- Website (VM 101): `net0: virtio,bridge=vmbr0,tag=20`
- Agent VMs: `net0: virtio,bridge=vmbr0,tag=30`

## Step 3: Firewall Rules

### Default Policy

- **Inter-VLAN**: Block all by default
- **Same VLAN**: Allow all
- **Outbound**: Allow all
- **Inbound**: Block all (except Cloudflare Tunnel)

### Allow Rules

Create firewall rules in UniFi under **Settings** → **Firewall & Security** → **Firewall Rules**

#### Rule 1: Production to NAS

```
Name: Production-to-NAS
Type: LAN In
Source: Production (VLAN 20)
Destination: 192.168.0.1 (UDM)
Port: 445, 2049 (SMB, NFS)
Action: Allow
```

#### Rule 2: Agents to Production API

```
Name: Agents-to-Production-API
Type: LAN In
Source: Agents (VLAN 30)
Destination: Production (VLAN 20)
Port: 8001 (MYCA API)
Action: Allow
```

#### Rule 3: Production to Agents

```
Name: Production-to-Agents
Type: LAN In
Source: Production (VLAN 20)
Destination: Agents (VLAN 30)
Port: 22, 8000-9000 (SSH, Agent ports)
Action: Allow
```

#### Rule 4: Management to All

```
Name: Management-Allow-All
Type: LAN In
Source: Management (VLAN 10)
Destination: Any
Action: Allow
```

#### Rule 5: IoT to Production (Limited)

```
Name: IoT-to-Production-Limited
Type: LAN In
Source: IoT (VLAN 40)
Destination: Production (VLAN 20)
Port: 8001 (MYCA API for MycoBrain)
Action: Allow
```

#### Rule 6: Block Guest

```
Name: Block-Guest-to-Private
Type: LAN In
Source: Guest (VLAN 50)
Destination: RFC1918 Networks
Action: Block
```

## Step 4: Port Assignments

### Static IPs for Critical Services

Configure DHCP reservations or static IPs:

| Device | VLAN | IP Address |
|--------|------|------------|
| MYCA Core VM | 20 | 192.168.20.10 |
| Website VM | 20 | 192.168.20.11 |
| Database VM | 20 | 192.168.20.12 |
| Proxmox Build | 10 | 192.168.10.2 |
| Proxmox DC1 | 10 | 192.168.10.3 |
| Proxmox DC2 | 10 | 192.168.10.4 |
| mycocomp | 1 | 192.168.0.100 (DHCP reservation) |

## Step 5: Additional Security

### Enable IDS/IPS

1. Go to **Settings** → **Firewall & Security** → **Threat Management**
2. Enable **Intrusion Detection System**
3. Set to **Protect** mode for active blocking

### Enable Traffic Rules

Create traffic rules for rate limiting:

1. Go to **Settings** → **Traffic Rules**
2. Create rule for API rate limiting

### Enable Honeypot (Optional)

1. Go to **Settings** → **Firewall & Security** → **Honeypot**
2. Enable honeypot on internal networks

## Step 6: Verification

### Test VLAN Connectivity

From a device on each VLAN:

```bash
# Test same-VLAN connectivity
ping 192.168.20.1  # Gateway

# Test cross-VLAN (should be blocked unless allowed)
ping 192.168.30.10  # Should fail if not allowed

# Test NAS access
ping 192.168.0.1
ls /mnt/mycosoft/  # Should work if firewall allows
```

### Test Firewall Rules

```bash
# From Production VLAN, test NAS
curl -I smb://192.168.0.1/mycosoft

# From Agent VLAN, test MYCA API
curl http://192.168.20.10:8001/health

# From Guest, test internal (should fail)
ping 192.168.20.10  # Should fail
```

## mycocomp Development Access

mycocomp (this machine) stays on the default VLAN (192.168.0.0/24) for development:

### Access Permissions

- Full access to NAS (192.168.0.1)
- Read-only access to Production VLAN (for testing)
- SSH access to all Proxmox nodes
- No direct access to Agent VMs (use MYCA API)

### Firewall Rule for mycocomp

```
Name: Mycocomp-Development-Access
Type: LAN In
Source: 192.168.0.100 (mycocomp)
Destination: Any
Action: Allow
```

## Troubleshooting

### VLAN Not Working

1. Check switch port profile is correct
2. Verify VLAN tag on Proxmox VM
3. Check VLAN bridge configuration on Proxmox
4. Verify DHCP is enabled on VLAN

### Firewall Blocking Legitimate Traffic

1. Check firewall rules order (processed top to bottom)
2. Add specific allow rule before block rules
3. Check traffic logs in UniFi

### Cannot Access NAS from VLAN

1. Verify NAS firewall allows VLAN subnet
2. Check NFS exports include VLAN subnet
3. Test from default network first
