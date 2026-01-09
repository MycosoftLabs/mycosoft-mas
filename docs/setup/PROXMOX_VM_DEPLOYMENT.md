# Proxmox VM Deployment Guide

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **Prerequisites**: Proxmox cluster access, SSH keys configured

This document covers the deployment of virtual machines on the Proxmox cluster for the MYCA infrastructure, including VM templates, always-on service configuration, and local AI model deployment.

---

## Table of Contents

1. [Cluster Overview](#cluster-overview)
2. [Cluster Configuration](#cluster-configuration)
3. [VM Templates](#vm-templates)
4. [MYCA Core VM](#myca-core-vm)
5. [Agent VMs](#agent-vms)
6. [Always-On Service Configuration](#always-on-service-configuration)
7. [Local AI Model Deployment](#local-ai-model-deployment)
8. [GPU Passthrough](#gpu-passthrough)
9. [High Availability Configuration](#high-availability-configuration)
10. [Proxmox API Integration](#proxmox-api-integration)
11. [Backup and Recovery](#backup-and-recovery)
12. [Troubleshooting](#troubleshooting)

---

## Cluster Overview

### Node Inventory

| Node | Hostname | IP Address | Role | Resources |
|------|----------|------------|------|-----------|
| **Build** | build.myca.local | 192.168.0.202 | Primary | 256GB RAM, 64 cores |
| **DC1** | dc1.myca.local | 192.168.0.2 | Secondary | 128GB RAM, 32 cores |
| **DC2** | dc2.myca.local | 192.168.0.131 | Secondary | 128GB RAM, 32 cores |

### Storage Configuration

| Storage | Type | Location | Use |
|---------|------|----------|-----|
| local | Directory | /var/lib/vz | ISOs, Templates |
| local-lvm | LVM | Node-local | VM Disks |
| nas-mycosoft | NFS | 192.168.0.1:/mycosoft | Shared Data |

### VM Distribution Plan

| VM | Primary Node | Failover | VLAN |
|----|--------------|----------|------|
| myca-core | Build | DC1 | 20 |
| myca-website | DC1 | DC2 | 20 |
| myca-database | DC2 | Build | 20 |
| agent-template | Build | - | 30 |
| agent-001..N | Any | Any | 30 |

---

## Cluster Configuration

### Step 1: Verify Cluster Status

```bash
# SSH to primary node
ssh root@192.168.0.202

# Check cluster status
pvecm status

# Expected output:
# Cluster information
# -------------------
# Name:             myca-cluster
# Config Version:   3
# Transport:        knet
# Secure auth:      on
# Quorum information
# ------------------
# ...
# Membership information
# ----------------------
# ...
```

### Step 2: Configure Shared Storage

Add NFS storage for shared data:

```bash
# On each node, add NAS storage
pvesm add nfs nas-mycosoft \
  --server 192.168.0.1 \
  --export /mycosoft \
  --path /mnt/pve/nas-mycosoft \
  --content images,rootdir,vztmpl,backup \
  --options vers=4
```

### Step 3: Configure VLAN-Aware Bridges

On each Proxmox node, edit `/etc/network/interfaces`:

```
# Management interface
auto vmbr0
iface vmbr0 inet static
    address 192.168.0.202/24
    gateway 192.168.0.1
    bridge-ports enp0s31f6
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

Apply changes:

```bash
ifreload -a
```

---

## VM Templates

### Base Template Configuration

Create a base Ubuntu 24.04 template for all VMs:

```bash
# Download Ubuntu cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

# Create VM template
qm create 9000 --name ubuntu-2404-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

# Import cloud image as disk
qm importdisk 9000 noble-server-cloudimg-amd64.img local-lvm

# Attach disk
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0

# Configure cloud-init
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0

# Set cloud-init defaults
qm set 9000 --ciuser myca
qm set 9000 --sshkeys ~/.ssh/authorized_keys
qm set 9000 --ipconfig0 ip=dhcp

# Convert to template
qm template 9000
```

### Agent Template

Use the provided script:

```bash
python scripts/proxmox/create_agent_template.py create \
  --host 192.168.0.202 \
  --token-id myca@pam!automation \
  --token-secret <secret>

# Or dry-run first
python scripts/proxmox/create_agent_template.py create --dry-run
```

**Agent Template Specifications:**

| Setting | Value |
|---------|-------|
| Template ID | 9001 |
| Name | myca-agent-template |
| Memory | 4096 MB |
| Cores | 2 |
| Disk | 32 GB |
| Network | VLAN 30 |
| OS | Ubuntu 24.04 |

---

## MYCA Core VM

### Creation

Use the provided script:

```bash
python scripts/proxmox/create_myca_core_vm.py \
  --host 192.168.0.202 \
  --token-id myca@pam!automation \
  --token-secret <secret>

# Or dry-run first
python scripts/proxmox/create_myca_core_vm.py --dry-run
```

### Manual Creation (Alternative)

```bash
# Clone from template
qm clone 9000 100 --name myca-core --full

# Resize disk
qm resize 100 scsi0 +98G  # Total 100GB

# Configure resources
qm set 100 --memory 32768 --cores 8 --cpu cputype=host

# Configure network (VLAN 20)
qm set 100 --net0 virtio,bridge=vmbr0,tag=20

# Set static IP via cloud-init
qm set 100 --ipconfig0 ip=192.168.20.10/24,gw=192.168.20.1

# Start VM
qm start 100
```

### MYCA Core VM Specifications

| Setting | Value |
|---------|-------|
| VM ID | 100 |
| Name | myca-core |
| Memory | 32 GB |
| Cores | 8 |
| Disk | 100 GB |
| Network | VLAN 20, IP: 192.168.20.10 |
| Node | Build (primary), DC1 (failover) |

### Post-Creation Setup

SSH into the VM and configure:

```bash
ssh myca@192.168.20.10

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker myca

# Mount NAS
sudo mkdir -p /mnt/mycosoft
echo "192.168.0.1:/mycosoft /mnt/mycosoft nfs4 defaults,_netdev,noatime 0 0" | sudo tee -a /etc/fstab
sudo mount -a

# Clone MYCA codebase
git clone https://github.com/mycosoft/mycosoft-mas.git /opt/myca
cd /opt/myca

# Copy production environment
cp config/production.env .env

# Start services
docker compose up -d
```

---

## Agent VMs

### Creating Agent VMs

Clone from the agent template:

```bash
# Create agent VM from template
qm clone 9001 200 --name agent-001 --full

# Set unique IP (or use DHCP)
qm set 200 --ipconfig0 ip=192.168.30.10/24,gw=192.168.30.1

# Start
qm start 200
```

### Automated Agent Creation

The MYCA orchestrator can create agent VMs dynamically via the Proxmox API:

```python
from infra.bootstrap.proxmox_client import ProxmoxClient

client = ProxmoxClient(
    host="192.168.0.202",
    token_id="myca@pam!automation",
    token_secret="<secret>"
)

# Clone new agent
new_vm = client.clone_vm(
    template_id=9001,
    new_id=201,
    name="agent-002",
    full_clone=True
)

# Start the new agent
client.start_vm(node="build", vmid=201)
```

### Agent VM Specifications

| Setting | Value |
|---------|-------|
| Template | 9001 |
| Memory | 4 GB |
| Cores | 2 |
| Disk | 32 GB |
| Network | VLAN 30 (DHCP) |
| Lifecycle | Ephemeral (can be destroyed) |

---

## Always-On Service Configuration

### Systemd Service Setup

For services that must run 24/7, configure systemd on each VM.

**MYCA Orchestrator Service:**

```bash
# Create systemd service file
sudo tee /etc/systemd/system/myca-orchestrator.service << 'EOF'
[Unit]
Description=MYCA Multi-Agent Orchestrator
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/myca
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable myca-orchestrator
sudo systemctl start myca-orchestrator
```

**Agent Runner Service:**

```bash
sudo tee /etc/systemd/system/myca-agent.service << 'EOF'
[Unit]
Description=MYCA Agent Runner
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=myca
WorkingDirectory=/opt/myca
Environment="PATH=/opt/myca/venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/myca/venv/bin/python -m mycosoft_mas.core.agent_runner
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### Docker Restart Policies

Ensure all containers restart automatically:

```yaml
# In docker-compose.yml
services:
  myca-api:
    restart: always
    deploy:
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
        window: 120s
  
  postgres:
    restart: always
  
  redis:
    restart: always
  
  qdrant:
    restart: always
```

### VM Auto-Start

Configure VMs to start automatically on node boot:

```bash
# Enable auto-start for MYCA Core
qm set 100 --onboot 1 --startup order=1

# Enable for website
qm set 101 --onboot 1 --startup order=2

# Enable for database
qm set 102 --onboot 1 --startup order=1,up=120
```

### Health Checks

Create a health check script:

```bash
#!/bin/bash
# /opt/myca/scripts/health_check.sh

services=(
  "http://localhost:8001/health"  # MYCA API
  "http://localhost:3000"         # Website
  "http://localhost:5432"         # PostgreSQL (nc check)
  "http://localhost:6379"         # Redis (nc check)
)

for service in "${services[@]}"; do
  if curl -sf "$service" > /dev/null 2>&1; then
    echo "[OK] $service"
  else
    echo "[FAIL] $service"
    # Optionally trigger alert
  fi
done
```

Add to crontab:

```bash
# Check every 5 minutes
*/5 * * * * /opt/myca/scripts/health_check.sh >> /var/log/myca-health.log 2>&1
```

---

## Local AI Model Deployment

### Ollama on myca-core

Install and configure Ollama for local LLM inference:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Configure to listen on all interfaces
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama

# Pull models
ollama pull llama3.1
ollama pull codellama
ollama pull mistral

# Verify
curl http://localhost:11434/api/tags
```

### Whisper for Speech-to-Text

Deploy Whisper as a Docker container:

```yaml
# Add to docker-compose.yml
whisper:
  image: onerahmet/openai-whisper-asr-webservice:latest
  restart: always
  ports:
    - "8765:9000"
  environment:
    ASR_MODEL: base.en
    ASR_ENGINE: openai_whisper
  volumes:
    - /mnt/mycosoft/shared/models:/root/.cache/whisper
```

### Model Storage

Store models on NAS for persistence:

```bash
# Ollama models
export OLLAMA_MODELS=/mnt/mycosoft/shared/models/ollama

# Whisper models (via volume mount)
# Already configured in docker-compose

# HuggingFace cache
export HF_HOME=/mnt/mycosoft/shared/models/huggingface
```

---

## GPU Passthrough

### Requirements

- IOMMU enabled in BIOS
- GPU dedicated to VM (not used by host)
- Proper driver isolation

### Configuration Steps

1. **Enable IOMMU on host:**

Edit `/etc/default/grub`:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"
```

Update GRUB:
```bash
update-grub
reboot
```

2. **Blacklist host GPU drivers:**

```bash
echo "blacklist nouveau" >> /etc/modprobe.d/blacklist.conf
echo "blacklist nvidia" >> /etc/modprobe.d/blacklist.conf
update-initramfs -u
```

3. **Configure VM for GPU passthrough:**

```bash
# Find GPU IOMMU group
find /sys/kernel/iommu_groups/ -type l

# Add GPU to VM (example: 01:00.0)
qm set 100 --hostpci0 01:00,pcie=1,x-vga=1
```

4. **Install NVIDIA drivers in VM:**

```bash
# Ubuntu VM
sudo apt install nvidia-driver-545 nvidia-cuda-toolkit
```

### GPU for AI Workloads

If a GPU is available on a Proxmox node:

```yaml
# docker-compose.yml with GPU
services:
  ollama:
    image: ollama/ollama:latest
    restart: always
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - /mnt/mycosoft/shared/models/ollama:/root/.ollama
```

---

## High Availability Configuration

### HA Group Setup

```bash
# Create HA group
ha-manager groupadd myca-production --nodes build,dc1,dc2 --nofailback 1

# Add VMs to HA
ha-manager add vm:100 --group myca-production --state started
ha-manager add vm:101 --group myca-production --state started
ha-manager add vm:102 --group myca-production --state started
```

### Failover Testing

```bash
# Simulate node failure (carefully!)
# On Build node:
systemctl stop pve-cluster

# Watch HA migrate VMs to other nodes
ha-manager status

# Restore
systemctl start pve-cluster
```

### Resource Limits

Set resource limits to prevent overcommitment:

```bash
# Set memory balloon (allow dynamic adjustment)
qm set 100 --balloon 16384  # Minimum 16GB

# Set CPU limits
qm set 100 --cpulimit 4  # Max 4 cores during contention
```

---

## Proxmox API Integration

### API Token Creation

```bash
# Create API user
pveum user add myca@pam
pveum passwd myca@pam

# Create API token
pveum user token add myca@pam automation --privsep=0

# Save the token secret! It's only shown once.

# Grant permissions
pveum aclmod / -user myca@pam -role Administrator
```

### Environment Variables

```bash
# config/production.env
PROXMOX_HOST_BUILD=192.168.0.202
PROXMOX_HOST_DC1=192.168.0.2
PROXMOX_HOST_DC2=192.168.0.131
PROXMOX_PORT=8006
PROXMOX_TOKEN_ID=myca@pam!automation
PROXMOX_TOKEN_SECRET=<from-above>
```

### Using the Proxmox Client

```python
from infra.bootstrap.proxmox_client import ProxmoxClient

client = ProxmoxClient(
    host=os.environ["PROXMOX_HOST_BUILD"],
    token_id=os.environ["PROXMOX_TOKEN_ID"],
    token_secret=os.environ["PROXMOX_TOKEN_SECRET"]
)

# List VMs
vms = client.list_vms()
for vm in vms:
    print(f"VM {vm['vmid']}: {vm['name']} - {vm['status']}")

# Create snapshot
client.create_snapshot(node="build", vmid=100, name="before-update")

# Reboot VM
client.reboot_vm(node="build", vmid=100)

# Get VM status
status = client.get_vm_status(node="build", vmid=100)
print(f"CPU: {status['cpu']}%, Memory: {status['mem']}%")
```

---

## Backup and Recovery

### Automated Backups

Configure backup schedule in Proxmox:

1. Navigate to **Datacenter** > **Backup**
2. Add backup job:

| Setting | Value |
|---------|-------|
| Storage | nas-mycosoft |
| Schedule | Daily at 02:00 |
| Mode | Snapshot |
| Compression | ZSTD |
| Retention | Keep last 7 |

### Manual Backup

```bash
# Backup specific VM
vzdump 100 --storage nas-mycosoft --mode snapshot --compress zstd

# Restore from backup
qmrestore /mnt/pve/nas-mycosoft/dump/vzdump-qemu-100-*.vma.zst 100 --storage local-lvm
```

### Disaster Recovery

1. **Full cluster failure:**
   - Restore from NAS backups to any working node
   - Update DNS/Cloudflare tunnel to new IPs

2. **Single node failure:**
   - HA automatically migrates VMs
   - Verify services are running
   - Replace/repair failed node

3. **Data corruption:**
   - Restore from daily backups on NAS
   - Database point-in-time recovery from PostgreSQL WAL

---

## Troubleshooting

### VM Won't Start

```bash
# Check VM status
qm status 100

# View VM config
qm config 100

# Check logs
journalctl -u pve-guests@100

# Common fixes:
# - Insufficient resources: reduce memory/cores
# - Network issue: verify bridge config
# - Disk issue: check storage availability
```

### Network Issues

```bash
# Check VM network from host
qm monitor 100
> info network

# Inside VM
ip addr
ping 192.168.20.1  # Gateway

# Check VLAN tagging
tcpdump -i vmbr0 -e vlan
```

### NAS Mount Issues

```bash
# Check NFS on Proxmox host
showmount -e 192.168.0.1

# Check mount status
mount | grep mycosoft

# Remount
pvesm set nas-mycosoft --disable 1
pvesm set nas-mycosoft --disable 0
```

### API Connection Issues

```bash
# Test API from external machine
curl -k "https://192.168.0.202:8006/api2/json/version" \
  -H "Authorization: PVEAPIToken=myca@pam!automation=<secret>"

# Check API service
systemctl status pveproxy

# View API logs
journalctl -u pveproxy -f
```

---

## Maintenance Checklist

### Daily

- [ ] Verify all VMs are running
- [ ] Check HA status
- [ ] Review system logs

### Weekly

- [ ] Verify backup completion
- [ ] Check storage utilization
- [ ] Review resource usage trends

### Monthly

- [ ] Apply Proxmox updates
- [ ] Test failover procedures
- [ ] Review and rotate API tokens
- [ ] Audit VM configurations

---

## Related Documents

- [MASTER_SETUP_GUIDE.md](./MASTER_SETUP_GUIDE.md) - Overall architecture
- [UBIQUITI_NETWORK_INTEGRATION.md](./UBIQUITI_NETWORK_INTEGRATION.md) - Network setup
- [SECURITY_HARDENING_GUIDE.md](./SECURITY_HARDENING_GUIDE.md) - Security configuration
- [docs/infrastructure/PROXMOX_HA_CLUSTER.md](../infrastructure/PROXMOX_HA_CLUSTER.md) - HA details

---

*Document maintained by MYCA Infrastructure Team*
