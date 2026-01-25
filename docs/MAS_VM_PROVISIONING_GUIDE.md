# MAS VM Provisioning Guide

## Overview

This guide covers provisioning a dedicated VM for the MAS v2 Agent Runtime System.

## VM Specifications

| Resource | Allocation |
|----------|------------|
| CPU | 16 cores |
| RAM | 64 GB |
| Storage | 500 GB NVMe |
| Network | 10 Gbps to switch |
| GPU | Optional (for NLM training) |

## Proxmox VM Creation

### 1. Create VM via Proxmox UI or API

```bash
# Using Proxmox API
curl -X POST "https://proxmox.mycosoft.local:8006/api2/json/nodes/pve1/qemu" \
  -H "Authorization: PVEAPIToken=mas@pve!mas-token=<TOKEN>" \
  -d "vmid=188" \
  -d "name=mas-vm" \
  -d "memory=65536" \
  -d "cores=16" \
  -d "sockets=1" \
  -d "cpu=host" \
  -d "ostype=l26" \
  -d "scsihw=virtio-scsi-single" \
  -d "scsi0=local-lvm:500,discard=on,iothread=1,ssd=1" \
  -d "net0=virtio,bridge=vmbr0,firewall=1" \
  -d "boot=order=scsi0;net0" \
  -d "agent=1"
```

### 2. Install Ubuntu Server 22.04 LTS

- Download ISO: ubuntu-22.04-live-server-amd64.iso
- Mount as CD-ROM
- Install with minimal packages

### 3. Post-Installation Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Install Redis
sudo apt install redis-server -y
sudo systemctl enable redis-server

# Install monitoring tools
sudo apt install htop iotop nload -y
```

## Network Configuration

### Static IP Assignment

Edit `/etc/netplan/00-installer-config.yaml`:

```yaml
network:
  version: 2
  ethernets:
    ens18:
      addresses:
        - 192.168.0.188/24
      routes:
        - to: default
          via: 192.168.0.1
      nameservers:
        addresses:
          - 192.168.0.1
          - 8.8.8.8
```

Apply: `sudo netplan apply`

### Firewall Rules

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 8001/tcp    # Orchestrator
sudo ufw allow 6379/tcp    # Redis (internal only)
sudo ufw allow 8080/tcp    # Agent health checks
sudo ufw enable
```

## Docker Configuration

### Create Docker Network

```bash
docker network create mas-network
```

### Docker Daemon Settings

Edit `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
```

Restart Docker: `sudo systemctl restart docker`

## Redis Cluster Setup (Optional)

For high availability, set up a 3-node Redis cluster:

```yaml
# docker-compose.redis-cluster.yml
version: '3.8'

services:
  redis-node-1:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000
    ports:
      - "6379:6379"
    volumes:
      - redis-data-1:/data

  redis-node-2:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000
    ports:
      - "6380:6379"
    volumes:
      - redis-data-2:/data

  redis-node-3:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000
    ports:
      - "6381:6379"
    volumes:
      - redis-data-3:/data

volumes:
  redis-data-1:
  redis-data-2:
  redis-data-3:
```

## Deploy MAS Stack

### Clone Repository

```bash
cd /opt
sudo mkdir -p mycosoft
sudo chown $USER:$USER mycosoft
cd mycosoft
git clone https://github.com/mycosoft/mycosoft-mas.git
cd mycosoft-mas
```

### Build Agent Image

```bash
docker build -t mycosoft/mas-agent:latest -f docker/Dockerfile.agent .
```

### Start Services

```bash
docker compose -f docker/docker-compose.agents.yml up -d
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'orchestrator'
    static_configs:
      - targets: ['localhost:8001']
  
  - job_name: 'agents'
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: [__meta_docker_container_label_mas_agent]
        regex: true
        action: keep
```

### Grafana Dashboard

Import the MAS dashboard from `grafana/dashboards/mas-overview.json`.

## Snapshot Strategy

| Type | Frequency | Retention |
|------|-----------|-----------|
| Agent state | Every task completion | 24 hours |
| Container snapshot | Daily | 7 days |
| VM snapshot | Weekly | 30 days |
| Full backup | Monthly | 1 year |

### Automated VM Snapshots

```bash
# /etc/cron.d/mas-snapshots
0 2 * * * root /opt/mycosoft/scripts/create_vm_snapshot.sh
0 3 * * 0 root /opt/mycosoft/scripts/cleanup_old_snapshots.sh
```

## Health Checks

### Orchestrator Health

```bash
curl http://localhost:8001/health
```

### Agent Pool Status

```bash
curl http://localhost:8001/agents
```

### Redis Status

```bash
redis-cli ping
```

## Troubleshooting

### Agent Container Not Starting

```bash
# Check logs
docker logs mas-agent-<agent-id>

# Check resource usage
docker stats

# Inspect container
docker inspect mas-agent-<agent-id>
```

### Redis Connection Issues

```bash
# Test connection
redis-cli -h localhost -p 6379 ping

# Check Redis logs
sudo journalctl -u redis-server -f
```

### High Memory Usage

```bash
# Find memory-hungry containers
docker stats --no-stream | sort -k4 -h -r

# Force cleanup
docker system prune -f
```

## Environment Variables

Create `/opt/mycosoft/.env`:

```bash
# MAS Configuration
REDIS_URL=redis://localhost:6379/0
MINDEX_URL=http://192.168.0.187:8000
ORCHESTRATOR_URL=http://localhost:8001

# Integration Keys
PROXMOX_HOST=192.168.0.100
PROXMOX_TOKEN=<token>
UNIFI_HOST=192.168.1.1
UNIFI_USERNAME=<username>
UNIFI_PASSWORD=<password>
ELEVENLABS_API_KEY=<key>
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>

# Logging
LOG_LEVEL=INFO
```

## Security Considerations

1. **No root containers**: All agents run as non-root user
2. **Resource limits**: CPU and memory limits on all containers
3. **Network isolation**: mas-network is isolated
4. **Secrets management**: Use Docker secrets or Vault
5. **SSH key-only**: Disable password authentication
6. **Regular updates**: Automated security patches

## Next Steps

1. Provision VM in Proxmox
2. Run initial setup script
3. Deploy MAS stack
4. Verify orchestrator health
5. Spawn initial agents
6. Configure monitoring
7. Set up alerting
8. Document agent configurations
