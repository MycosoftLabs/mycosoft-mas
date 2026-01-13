# Proxmox Deployment Plan for 24/7 Operation

**Version**: 1.0.0  
**Date**: 2026-01-10  
**Status**: Production Ready  

---

## Executive Summary

This document outlines the deployment strategy for running the Mycosoft platform on Proxmox VE for 24/7 production operation. The architecture distributes services across dedicated VMs for isolation, scalability, and fault tolerance.

---

## VM Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PROXMOX CLUSTER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│   │   VM-100      │  │   VM-101      │  │   VM-102      │                   │
│   │   MINDEX      │  │   WEBSITE     │  │   MAS         │                   │
│   │   PostgreSQL  │  │   Next.js     │  │   Orchestrator│                   │
│   │   :8000/:5432 │  │   :3000       │  │   :8001       │                   │
│   │   4 CPU/8GB   │  │   2 CPU/4GB   │  │   4 CPU/8GB   │                   │
│   └───────────────┘  └───────────────┘  └───────────────┘                   │
│                                                                              │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│   │   VM-103      │  │   VM-104      │  │   VM-105      │                   │
│   │   MYCOBRAIN   │  │   MONITORING  │  │   N8N         │                   │
│   │   USB Pass    │  │   Grafana     │  │   Workflows   │                   │
│   │   :8003       │  │   Prometheus  │  │   :5678       │                   │
│   │   2 CPU/2GB   │  │   2 CPU/4GB   │  │   2 CPU/4GB   │                   │
│   └───────────────┘  └───────────────┘  └───────────────┘                   │
│                                                                              │
│   ┌───────────────┐  ┌───────────────┐                                      │
│   │   VM-106      │  │   VM-107      │                                      │
│   │   REDIS       │  │   QDRANT      │                                      │
│   │   Cache       │  │   Vector DB   │                                      │
│   │   :6379       │  │   :6333       │                                      │
│   │   1 CPU/2GB   │  │   2 CPU/4GB   │                                      │
│   └───────────────┘  └───────────────┘                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## VM Specifications

| VM ID | Name | Purpose | CPU | RAM | Disk | Network |
|-------|------|---------|-----|-----|------|---------|
| 100 | mindex | MINDEX API + PostgreSQL | 4 | 8GB | 100GB SSD | VLAN 10 |
| 101 | website | Next.js Website | 2 | 4GB | 50GB SSD | VLAN 20 |
| 102 | mas-orchestrator | MAS + MYCA Agents | 4 | 8GB | 50GB SSD | VLAN 10 |
| 103 | mycobrain | MycoBrain Service | 2 | 2GB | 20GB SSD | VLAN 10 |
| 104 | monitoring | Grafana + Prometheus | 2 | 4GB | 100GB SSD | VLAN 30 |
| 105 | n8n | n8n Workflows | 2 | 4GB | 50GB SSD | VLAN 10 |
| 106 | redis | Redis Cache | 1 | 2GB | 20GB SSD | VLAN 10 |
| 107 | qdrant | Qdrant Vector DB | 2 | 4GB | 50GB SSD | VLAN 10 |

**Total Resources**: 19 vCPU, 36GB RAM, 440GB Storage

---

## Network Architecture

### VLAN Configuration

| VLAN | Name | CIDR | Purpose |
|------|------|------|---------|
| 10 | Internal | 10.10.10.0/24 | Backend services |
| 20 | DMZ | 10.10.20.0/24 | Web-facing services |
| 30 | Management | 10.10.30.0/24 | Monitoring, admin |
| 40 | IoT | 10.10.40.0/24 | MycoBrain devices |

### IP Assignments

| VM | IP Address | Purpose |
|----|------------|---------|
| mindex | 10.10.10.10 | Database API |
| website | 10.10.20.10 | Public website |
| mas-orchestrator | 10.10.10.20 | Agent orchestration |
| mycobrain | 10.10.40.10 | Device management |
| monitoring | 10.10.30.10 | Grafana/Prometheus |
| n8n | 10.10.10.30 | Workflow automation |
| redis | 10.10.10.40 | Cache |
| qdrant | 10.10.10.50 | Vector store |

---

## VM Creation Scripts

### Create Base Template

```bash
#!/bin/bash
# create_template.sh - Creates base Ubuntu 24.04 template

# Download cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

# Create VM template
qm create 9000 --name ubuntu-template --memory 2048 --net0 virtio,bridge=vmbr0

# Import disk
qm importdisk 9000 noble-server-cloudimg-amd64.img local-lvm

# Attach disk
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0

# Set boot
qm set 9000 --boot c --bootdisk scsi0

# Add cloud-init drive
qm set 9000 --ide2 local-lvm:cloudinit

# Convert to template
qm template 9000
```

### Create Service VMs

```bash
#!/bin/bash
# create_vms.sh - Creates all service VMs from template

# MINDEX VM
qm clone 9000 100 --name mindex --full
qm set 100 --cores 4 --memory 8192 --ciuser mindex --cipassword "SecurePass123!"
qm set 100 --net0 virtio,bridge=vmbr0,tag=10
qm resize 100 scsi0 100G
qm start 100

# Website VM
qm clone 9000 101 --name website --full
qm set 101 --cores 2 --memory 4096 --ciuser website --cipassword "SecurePass123!"
qm set 101 --net0 virtio,bridge=vmbr0,tag=20
qm resize 101 scsi0 50G
qm start 101

# MAS Orchestrator VM
qm clone 9000 102 --name mas-orchestrator --full
qm set 102 --cores 4 --memory 8192 --ciuser mas --cipassword "SecurePass123!"
qm set 102 --net0 virtio,bridge=vmbr0,tag=10
qm resize 102 scsi0 50G
qm start 102

# MycoBrain VM with USB passthrough
qm clone 9000 103 --name mycobrain --full
qm set 103 --cores 2 --memory 2048 --ciuser mycobrain --cipassword "SecurePass123!"
qm set 103 --net0 virtio,bridge=vmbr0,tag=40
qm set 103 --usb0 host=10c4:ea60  # Silicon Labs CP210x
qm start 103

# Monitoring VM
qm clone 9000 104 --name monitoring --full
qm set 104 --cores 2 --memory 4096 --ciuser monitoring --cipassword "SecurePass123!"
qm set 104 --net0 virtio,bridge=vmbr0,tag=30
qm resize 104 scsi0 100G
qm start 104

# n8n VM
qm clone 9000 105 --name n8n --full
qm set 105 --cores 2 --memory 4096 --ciuser n8n --cipassword "SecurePass123!"
qm set 105 --net0 virtio,bridge=vmbr0,tag=10
qm resize 105 scsi0 50G
qm start 105

# Redis VM
qm clone 9000 106 --name redis --full
qm set 106 --cores 1 --memory 2048 --ciuser redis --cipassword "SecurePass123!"
qm set 106 --net0 virtio,bridge=vmbr0,tag=10
qm start 106

# Qdrant VM
qm clone 9000 107 --name qdrant --full
qm set 107 --cores 2 --memory 4096 --ciuser qdrant --cipassword "SecurePass123!"
qm set 107 --net0 virtio,bridge=vmbr0,tag=10
qm resize 107 scsi0 50G
qm start 107
```

---

## Docker Installation on VMs

```bash
#!/bin/bash
# install_docker.sh - Run on each VM

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add user to docker group
usermod -aG docker $USER

# Enable Docker on boot
systemctl enable docker
systemctl start docker

# Install Docker Compose
apt-get install docker-compose-plugin -y
```

---

## Service Deployment

### VM-100: MINDEX

```bash
# On mindex VM
cd /opt
git clone https://github.com/mycosoft/mindex.git
cd mindex

# Create .env
cat << 'EOF' > .env
MINDEX_DB_HOST=localhost
MINDEX_DB_PORT=5432
MINDEX_DB_USER=mindex
MINDEX_DB_PASSWORD=SecureMindexPass!
MINDEX_DB_NAME=mindex
MINDEX_API_PORT=8000
MINDEX_API_KEY=production-api-key-here
EOF

# Start services
docker compose up -d
```

### VM-101: Website

```bash
# On website VM
cd /opt
git clone https://github.com/mycosoft/website.git
cd website

# Create .env.local
cat << 'EOF' > .env.local
MINDEX_API_URL=http://10.10.10.10:8000
MINDEX_API_KEY=production-api-key-here
NEXTAUTH_SECRET=production-secret-here
NEXTAUTH_URL=https://mycosoft.io
EOF

# Build and start
npm install
npm run build
npm run start
```

### VM-102: MAS Orchestrator

```bash
# On mas-orchestrator VM
cd /opt
git clone https://github.com/mycosoft/mas.git
cd mas

# Start MAS orchestrator
docker compose up -d
```

### VM-103: MycoBrain

```bash
# On mycobrain VM
# USB device should be visible
lsusb | grep "Silicon Labs"

# Start MycoBrain service
docker run -d \
  --name mycobrain \
  --restart unless-stopped \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  --device /dev/ttyUSB1:/dev/ttyUSB1 \
  -p 8003:8003 \
  -e MINDEX_API_URL=http://10.10.10.10:8000 \
  mycosoft/mycobrain:latest
```

---

## High Availability Configuration

### Automatic Restart

```bash
# Create systemd service for each container
cat << 'EOF' > /etc/systemd/system/mycosoft-mindex.service
[Unit]
Description=Mycosoft MINDEX Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/docker compose -f /opt/mindex/docker-compose.yml up -d
ExecStop=/usr/bin/docker compose -f /opt/mindex/docker-compose.yml down
WorkingDirectory=/opt/mindex

[Install]
WantedBy=multi-user.target
EOF

systemctl enable mycosoft-mindex.service
```

### Health Checks

```yaml
# prometheus.yml - Add to monitoring VM
scrape_configs:
  - job_name: 'mindex'
    static_configs:
      - targets: ['10.10.10.10:8000']
    metrics_path: '/api/mindex/health'
    
  - job_name: 'website'
    static_configs:
      - targets: ['10.10.20.10:3000']
    metrics_path: '/api/health'
    
  - job_name: 'mas'
    static_configs:
      - targets: ['10.10.10.20:8001']
    metrics_path: '/health'
    
  - job_name: 'mycobrain'
    static_configs:
      - targets: ['10.10.40.10:8003']
    metrics_path: '/health'
```

---

## Backup Strategy

### Daily Backups

```bash
#!/bin/bash
# backup.sh - Run daily via cron

DATE=$(date +%Y%m%d)
BACKUP_DIR=/mnt/nas/backups/proxmox

# Backup VMs
for VMID in 100 101 102 103 104 105 106 107; do
  vzdump $VMID --compress zstd --storage nas --mode snapshot
done

# Backup configs
tar -czf $BACKUP_DIR/configs-$DATE.tar.gz /etc/pve/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.zst" -mtime +7 -delete
```

### Database Backup (MINDEX)

```bash
#!/bin/bash
# mindex_backup.sh - Run hourly

DATE=$(date +%Y%m%d_%H%M)
ssh 10.10.10.10 "docker exec mindex-postgres pg_dump -U mindex mindex | gzip" > /mnt/nas/backups/mindex/mindex-$DATE.sql.gz

# Keep 24 hours of hourly backups
find /mnt/nas/backups/mindex -name "*.sql.gz" -mtime +1 -delete
```

---

## Monitoring & Alerting

### Grafana Dashboards

1. **System Overview** - CPU, Memory, Disk across all VMs
2. **MINDEX Metrics** - API response times, database queries
3. **MycoBrain Devices** - Connected devices, telemetry rate
4. **Website Performance** - Page load times, error rates

### Alert Rules

```yaml
# alertmanager.yml
route:
  receiver: 'mycosoft-team'
  group_by: ['alertname', 'severity']

receivers:
  - name: 'mycosoft-team'
    slack_configs:
      - channel: '#alerts'
        api_url: 'https://hooks.slack.com/services/xxx'
    email_configs:
      - to: 'ops@mycosoft.io'
```

---

## Security Hardening

### Firewall Rules

```bash
# Allow only necessary ports between VMs
iptables -A INPUT -s 10.10.10.0/24 -j ACCEPT
iptables -A INPUT -s 10.10.20.0/24 -j ACCEPT
iptables -A INPUT -s 10.10.30.0/24 -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -j DROP
```

### SSL/TLS

All external-facing services should use TLS:
- Nginx reverse proxy with Let's Encrypt
- Internal services use mTLS where possible

---

## Maintenance Procedures

### VM Updates

```bash
# Update all VMs
for IP in 10.10.10.10 10.10.10.20 10.10.10.30 10.10.20.10 10.10.30.10 10.10.40.10; do
  ssh $IP "apt-get update && apt-get upgrade -y"
done
```

### Container Updates

```bash
# Pull latest images and restart
docker compose pull
docker compose up -d
```

---

## Disaster Recovery

### Recovery Time Objective (RTO): 1 hour
### Recovery Point Objective (RPO): 1 hour

### Recovery Steps

1. Restore VMs from backup
2. Restore database from latest backup
3. Verify service connectivity
4. Test all endpoints
5. Resume normal operations

---

## Related Documents

- [Master Architecture](./MASTER_ARCHITECTURE.md)
- [MycoBrain COM Port Management](./MYCOBRAIN_COM_PORT_MANAGEMENT.md)
- [Port Assignments](../PORT_ASSIGNMENTS.md)

---

*Last Updated: 2026-01-10*
