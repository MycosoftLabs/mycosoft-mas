# Proxmox HA Cluster Configuration

This document describes the Proxmox High Availability cluster setup for MYCA production environment.

## Cluster Overview

| Node | IP Address | Role | Resources |
|------|------------|------|-----------|
| Build | 192.168.0.202 | Primary (MYCA Core) | High compute |
| DC1 | 192.168.0.2 | Secondary (Agents, Website) | Medium compute |
| DC2 | 192.168.0.131 | Tertiary (Agents, Database) | Medium compute |

## Prerequisites

1. All three Proxmox nodes are installed and accessible
2. SSH access to all nodes (root or sudo)
3. NFS storage mounted from UDM Pro 26TB
4. Network connectivity between all nodes

## Step 1: Create Cluster

On the first node (Build - 192.168.0.202):

```bash
# Create the cluster
pvecm create mycosoft-cluster

# Verify cluster status
pvecm status
```

## Step 2: Join Additional Nodes

On DC1 (192.168.0.2):

```bash
# Join the cluster
pvecm add 192.168.0.202

# Verify
pvecm status
```

On DC2 (192.168.0.131):

```bash
# Join the cluster
pvecm add 192.168.0.202

# Verify
pvecm status
```

## Step 3: Configure Shared Storage

Add NFS storage to all nodes:

```bash
# On any cluster node
pvesm add nfs mycosoft-nas \
  --server 192.168.0.1 \
  --export /mycosoft \
  --content images,rootdir,vztmpl,backup \
  --options vers=4
```

Verify storage:

```bash
pvesm status
```

## Step 4: Configure HA

Enable HA on the cluster:

```bash
# Enable fencing (required for HA)
pvecm expected 1

# Check HA status
ha-manager status
```

## VM Specifications

### MYCA Core VM (Production Orchestrator)

| Setting | Value |
|---------|-------|
| **VM ID** | 100 |
| **Name** | myca-core |
| **Node** | Build (primary) |
| **vCPUs** | 8 |
| **RAM** | 32GB |
| **Disk** | 100GB (local-lvm) |
| **Storage Mount** | /mnt/mycosoft (NFS) |
| **OS** | Ubuntu 24.04 LTS |
| **Network** | VLAN 20 (Production) |
| **HA** | Enabled, priority 100 |

### Agent Pool VM Template

| Setting | Value |
|---------|-------|
| **Template ID** | 9000 |
| **Name** | myca-agent-template |
| **vCPUs** | 4 |
| **RAM** | 8GB |
| **Disk** | 50GB |
| **OS** | Ubuntu 24.04 LTS (cloud-init) |
| **Network** | VLAN 30 (Agents) |

### Website VM

| Setting | Value |
|---------|-------|
| **VM ID** | 101 |
| **Name** | myca-website |
| **Node** | DC1 (primary) |
| **vCPUs** | 4 |
| **RAM** | 8GB |
| **Disk** | 50GB |
| **OS** | Ubuntu 24.04 LTS |
| **Network** | VLAN 20 (Production) |
| **HA** | Enabled, priority 90 |

### Database VM

| Setting | Value |
|---------|-------|
| **VM ID** | 102 |
| **Name** | myca-database |
| **Node** | DC2 (primary) |
| **vCPUs** | 4 |
| **RAM** | 16GB |
| **Disk** | NFS (mycosoft-nas) |
| **OS** | Ubuntu 24.04 LTS |
| **Network** | VLAN 20 (Production) |
| **HA** | Enabled, priority 95 |

## Create MYCA Core VM

Using the Proxmox API via Python script:

```python
from proxmox_client import ProxmoxClient

# Connect to Proxmox
client = ProxmoxClient(
    host="192.168.0.202",
    token_id="myca@pve!mas",
    token_secret="your-token-secret"
)

# Create MYCA Core VM
client.create_vm(
    node="build",
    vmid=100,
    name="myca-core",
    cores=8,
    memory=32768,
    scsihw="virtio-scsi-pci",
    scsi0="local-lvm:100,format=qcow2",
    ide2="local:iso/ubuntu-24.04-live-server-amd64.iso,media=cdrom",
    net0="virtio,bridge=vmbr0,tag=20",
    ostype="l26",
    boot="order=scsi0;ide2",
    agent=1
)
```

## HA Configuration

Add VMs to HA:

```bash
# Add MYCA Core with high priority
ha-manager add vm:100 --state started --group ha-group --max_restart 3 --max_relocate 3

# Add Website VM
ha-manager add vm:101 --state started --group ha-group --max_restart 3 --max_relocate 3

# Add Database VM
ha-manager add vm:102 --state started --group ha-group --max_restart 3 --max_relocate 3
```

## HA Group Configuration

Create HA group with node preferences:

```bash
# Create HA group
ha-manager groupadd ha-group \
  --nodes build,dc1,dc2 \
  --restricted 1 \
  --nofailback 0

# Set node priorities (Build is primary)
# Edit /etc/pve/ha/groups.cfg
```

Example `/etc/pve/ha/groups.cfg`:

```
group: ha-group
    nodes build:100,dc1:90,dc2:80
    restricted 1
    nofailback 0
```

## NFS Mount on VMs

After VM creation, configure NFS mount:

```bash
# Install NFS client
apt update && apt install -y nfs-common

# Create mount point
mkdir -p /mnt/mycosoft

# Add to fstab
echo "192.168.0.1:/mycosoft /mnt/mycosoft nfs defaults,_netdev,nofail 0 0" >> /etc/fstab

# Mount
mount -a
```

## Monitoring HA Status

```bash
# Check HA status
ha-manager status

# Check node status
pvecm nodes

# Check cluster status
pvecm status

# View HA logs
journalctl -u pve-ha-lrm -f
```

## Failover Testing

Test HA failover:

```bash
# Simulate node failure (on Build node)
systemctl stop pve-ha-lrm

# VMs should migrate to DC1 or DC2 automatically
# Check on another node
ha-manager status

# Restart services
systemctl start pve-ha-lrm
```

## Backup Configuration

Configure automated backups to NAS:

```bash
# Create backup job (via API or UI)
# Schedule: Daily at 2:00 AM
# Storage: mycosoft-nas
# Mode: Snapshot
# Retention: 7 daily, 4 weekly, 12 monthly
```

## Troubleshooting

### Cluster Communication Issues

```bash
# Check corosync
systemctl status corosync
corosync-quorumtool -s

# Check network
ping 192.168.0.202
ping 192.168.0.2
ping 192.168.0.131
```

### HA Not Working

```bash
# Check fencing
pvecm expected

# Check HA manager
systemctl status pve-ha-crm
systemctl status pve-ha-lrm

# View logs
journalctl -u pve-ha-crm -f
```

### Storage Issues

```bash
# Check NFS mount
df -h /mnt/mycosoft

# Verify storage in Proxmox
pvesm status

# Test NFS
showmount -e 192.168.0.1
```

## Next Steps

After HA cluster is configured:

1. Create MYCA Core VM
2. Create Agent Template
3. Deploy Docker stack on MYCA Core
4. Configure database migration to NAS
