# MINDEX VM Specification - February 4, 2026
# Proxmox Virtual Environment Configuration

## VM Configuration

### Basic Settings
- **VM ID**: 105 (next available in sequence)
- **Name**: MINDEX-VM
- **Template**: No
- **Description**: Mycosoft MINDEX - Memory Index, Knowledge Graph, and Cryptographic Ledger Service

### Hardware
- **Memory**: 8192 MB (8 GB)
- **Cores**: 4 vCPU
- **CPU Type**: host
- **Sockets**: 1

### Storage
- **System Disk**: 100 GB (local-lvm:vm-105-disk-0)
  - Format: raw
  - Cache: writeback
  - SSD Emulation: Yes
- **Data Disk**: 200 GB (local-lvm:vm-105-disk-1)
  - Mounted at: /data
  - For PostgreSQL and ledger storage

### Network
- **Network Interface**: vmbr0
- **IP Address**: 192.168.0.189 (static)
- **Gateway**: 192.168.0.1
- **DNS**: 192.168.0.1, 8.8.8.8
- **Hostname**: mindex.mycosoft.local

### Operating System
- **OS Type**: Linux (l26)
- **ISO**: ubuntu-22.04.3-live-server-amd64.iso
- **Boot Order**: scsi0 (disk first)

## Proxmox CLI Commands

```bash
# Create VM
qm create 105 \
  --name MINDEX-VM \
  --memory 8192 \
  --cores 4 \
  --sockets 1 \
  --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-pci \
  --scsi0 local-lvm:100,format=raw,cache=writeback,ssd=1 \
  --scsi1 local-lvm:200,format=raw \
  --ide2 local:iso/ubuntu-22.04.3-live-server-amd64.iso,media=cdrom \
  --boot order=scsi0 \
  --ostype l26 \
  --description "Mycosoft MINDEX - Memory Index, Knowledge Graph, and Cryptographic Ledger Service"

# Start VM
qm start 105

# Configure static IP (after OS install)
# Edit /etc/netplan/00-installer-config.yaml on the VM
```

## Post-Installation Setup

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git curl wget htop
```

### 2. Configure Docker
```bash
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker mycosoft
```

### 3. Mount Data Disk
```bash
sudo mkfs.ext4 /dev/sdb
sudo mkdir -p /data
echo "/dev/sdb /data ext4 defaults 0 2" | sudo tee -a /etc/fstab
sudo mount -a
sudo chown -R mycosoft:mycosoft /data
```

### 4. Configure NAS Mount
```bash
sudo apt install -y cifs-utils
sudo mkdir -p /opt/mycosoft/ledger
echo "//192.168.0.105/mycosoft/ledger /opt/mycosoft/ledger cifs credentials=/etc/samba/credentials,uid=1000,gid=1000 0 0" | sudo tee -a /etc/fstab
```

### 5. Clone MAS Repository
```bash
cd /home/mycosoft
git clone https://github.com/mycosoft/mycosoft-mas.git
cd mycosoft-mas/infra/mindex-vm
```

### 6. Start Services
```bash
docker compose up -d
```

## Network Configuration

### Static IP (/etc/netplan/00-installer-config.yaml)
```yaml
network:
  version: 2
  ethernets:
    ens18:
      addresses:
        - 192.168.0.189/24
      routes:
        - to: default
          via: 192.168.0.1
      nameservers:
        addresses:
          - 192.168.0.1
          - 8.8.8.8
```

## Firewall Rules

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow PostgreSQL (internal only)
sudo ufw allow from 192.168.0.0/24 to any port 5432

# Allow Redis (internal only)
sudo ufw allow from 192.168.0.0/24 to any port 6379

# Allow MINDEX API
sudo ufw allow 8000/tcp

# Allow Ledger Service
sudo ufw allow 8100/tcp

# Enable firewall
sudo ufw enable
```

## Backup and Snapshot Schedule

- **Daily Snapshots**: 2:00 AM UTC (cron job)
- **Weekly Full Backup**: Sunday 3:00 AM UTC
- **Retention**: 7 daily snapshots, 4 weekly backups

## Monitoring

- **Prometheus endpoint**: http://192.168.0.189:9090/metrics
- **Health check**: http://192.168.0.189:8000/health
- **Grafana dashboard**: Integrated with main Grafana at 192.168.0.188

## Related VMs

| VM ID | Name | IP | Purpose |
|-------|------|------|---------|
| 101 | MAS-VM | 192.168.0.188 | Multi-Agent System Orchestrator |
| 102 | Website-Sandbox | 192.168.0.187 | Next.js Website |
| 103 | NAS | 192.168.0.105 | Network Attached Storage |
| 105 | MINDEX-VM | 192.168.0.189 | Memory Index & Ledger Service |
