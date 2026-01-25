# MYCA MAS Orchestrator VM Deployment Preparation

**Date:** January 24, 2026  
**Target VM ID:** 188  
**Target IP:** 192.168.0.188  
**Purpose:** Dedicated VM for MYCA Orchestrator and all 40+ MAS agents

---

## EXECUTIVE SUMMARY

This document provides the step-by-step preparation and deployment guide for creating a dedicated MYCA VM that will run the MAS v2 Orchestrator and all 40 agent containers. This VM represents MYCA's "brain" - the central intelligence that coordinates all Mycosoft operations.

---

## 1. PREREQUISITES CHECKLIST

### Hardware Requirements Verified

| Resource | Required | Available on Proxmox |
|----------|----------|----------------------|
| CPU Cores | 16 | ✅ 24 cores (X5670) |
| RAM | 64 GB | ✅ 118 GB total |
| Storage | 500 GB | ✅ 5.43 TB LVM |
| Network | 10 Gbps | ✅ 10G switch |

### Software Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Proxmox API Token | ✅ Ready | `root@pam!cursor_agent` |
| Ubuntu 22.04 ISO | ✅ Available | On Proxmox storage |
| Docker | To install | Via get.docker.com |
| Python 3.11 | To install | Via deadsnakes PPA |
| Redis | To install | Via apt |

### Code Ready

| Component | Status |
|-----------|--------|
| MAS v2 Runtime Engine | ✅ Complete |
| Orchestrator Service | ✅ Complete |
| 40 Agent Classes | ✅ Complete |
| Dockerfile.agent | ✅ Complete |
| docker-compose.agents.yml | ✅ Complete |
| Database Migration | ✅ Ready |

---

## 2. VM CREATION STEPS

### Step 2.1: Create VM via Proxmox API

```powershell
# From Windows Dev PC
$headers = @{
    "Authorization" = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
}

# Create VM 188
Invoke-RestMethod -Method Post -Uri "https://192.168.0.202:8006/api2/json/nodes/pve/qemu" `
    -Headers $headers `
    -SkipCertificateCheck `
    -Body @{
        vmid = 188
        name = "myca-orchestrator"
        memory = 65536
        cores = 16
        sockets = 1
        cpu = "host"
        ostype = "l26"
        scsihw = "virtio-scsi-single"
        "scsi0" = "local-lvm:500,discard=on,iothread=1,ssd=1"
        "net0" = "virtio,bridge=vmbr0,firewall=1"
        boot = "order=scsi0"
        agent = 1
    }
```

### Step 2.2: Attach Ubuntu ISO

```powershell
Invoke-RestMethod -Method Put -Uri "https://192.168.0.202:8006/api2/json/nodes/pve/qemu/188/config" `
    -Headers $headers `
    -SkipCertificateCheck `
    -Body @{
        ide2 = "local:iso/ubuntu-22.04-live-server-amd64.iso,media=cdrom"
    }
```

### Step 2.3: Start VM for Installation

```powershell
Invoke-RestMethod -Method Post -Uri "https://192.168.0.202:8006/api2/json/nodes/pve/qemu/188/status/start" `
    -Headers $headers `
    -SkipCertificateCheck
```

### Step 2.4: Manual Installation (via VNC Console)

1. Open Proxmox web UI: https://192.168.0.202:8006
2. Navigate to VM 188
3. Open Console (noVNC)
4. Install Ubuntu 22.04 with these settings:
   - Username: `mycosoft`
   - Hostname: `myca-orchestrator`
   - Enable SSH
   - Minimal installation

---

## 3. POST-INSTALLATION CONFIGURATION

### Step 3.1: Configure Static IP

SSH to VM (initial DHCP IP from Proxmox):

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

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

```bash
sudo netplan apply
```

### Step 3.2: Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3.3: Install Docker Compose

```bash
sudo apt update && sudo apt install -y docker-compose-plugin
```

### Step 3.4: Install Python 3.11

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

### Step 3.5: Install Redis

```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Step 3.6: Configure Firewall

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 8001/tcp    # Orchestrator
sudo ufw allow 6379/tcp    # Redis (internal)
sudo ufw allow 8080/tcp    # Agent health
sudo ufw enable
```

---

## 4. DEPLOY MAS STACK

### Step 4.1: Clone Repository

```bash
cd /opt
sudo mkdir -p mycosoft
sudo chown $USER:$USER mycosoft
cd mycosoft
git clone https://github.com/mycosoft/mycosoft-mas.git mas
cd mas
```

### Step 4.2: Create Environment File

```bash
cat > /opt/mycosoft/mas/.env << 'EOF'
# MAS Configuration
REDIS_URL=redis://localhost:6379/0
MINDEX_URL=http://192.168.0.187:8000
ORCHESTRATOR_URL=http://localhost:8001
QDRANT_URL=http://192.168.0.187:6333

# Agent Settings
LOG_LEVEL=INFO
HEALTH_CHECK_INTERVAL=30
HEARTBEAT_INTERVAL=10
TASK_TIMEOUT=300
MAX_CONCURRENT_TASKS=5

# Resource Limits
DEFAULT_CPU_LIMIT=1.0
DEFAULT_MEMORY_LIMIT=512

# Integration Keys (copy from secure storage)
PROXMOX_HOST=192.168.0.202
PROXMOX_TOKEN=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e
UNIFI_HOST=192.168.0.1
UNIFI_USERNAME=cursor_agent
# UNIFI_PASSWORD=<from-secure-storage>
# ELEVENLABS_API_KEY=<from-secure-storage>
# OPENAI_API_KEY=<from-secure-storage>
# ANTHROPIC_API_KEY=<from-secure-storage>
EOF
```

### Step 4.3: Build Agent Container Image

```bash
cd /opt/mycosoft/mas
docker build -t mycosoft/mas-agent:latest -f docker/Dockerfile.agent .
```

### Step 4.4: Create Docker Network

```bash
docker network create mas-network
```

### Step 4.5: Start MAS Stack

```bash
docker compose -f docker/docker-compose.agents.yml up -d
```

---

## 5. DATABASE MIGRATION

### Step 5.1: Connect to MINDEX Database

```bash
# From MYCA VM or Sandbox VM
psql -h 192.168.0.187 -U mas -d mindex
```

### Step 5.2: Run Migration

```sql
-- From migrations/003_agent_logging.sql
CREATE TABLE IF NOT EXISTS agent_logs (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_type VARCHAR(100),
    input_summary TEXT,
    output_summary TEXT,
    success BOOLEAN,
    duration_ms INTEGER,
    resources_used JSONB DEFAULT '{}',
    related_agents TEXT[] DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS agent_snapshots (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    snapshot_time TIMESTAMPTZ DEFAULT NOW(),
    state JSONB NOT NULL,
    config JSONB,
    pending_tasks JSONB DEFAULT '[]',
    memory_state JSONB,
    reason VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    cpu_percent FLOAT,
    memory_mb INTEGER,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_task_duration_ms FLOAT,
    messages_sent INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    uptime_seconds INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0
);

CREATE INDEX idx_agent_logs_agent_id ON agent_logs(agent_id);
CREATE INDEX idx_agent_logs_timestamp ON agent_logs(timestamp DESC);
CREATE INDEX idx_agent_snapshots_agent_id ON agent_snapshots(agent_id);
CREATE INDEX idx_agent_metrics_agent_id ON agent_metrics(agent_id);
CREATE INDEX idx_agent_metrics_timestamp ON agent_metrics(timestamp DESC);
```

---

## 6. VERIFICATION

### Step 6.1: Check Orchestrator Health

```bash
curl http://localhost:8001/health
# Expected: {"status":"ok","service":"myca-orchestrator"}
```

### Step 6.2: List Agents

```bash
curl http://localhost:8001/agents
# Expected: List of registered agents
```

### Step 6.3: Check Redis

```bash
redis-cli ping
# Expected: PONG
```

### Step 6.4: Spawn First Agent

```bash
curl -X POST http://localhost:8001/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"myca-core","agent_type":"core","category":"core"}'
```

### Step 6.5: Verify Container Running

```bash
docker ps | grep mas-agent
```

---

## 7. MONITORING SETUP

### Step 7.1: Create Prometheus Config

```bash
cat > /etc/prometheus/prometheus.yml << 'EOF'
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
EOF
```

### Step 7.2: Connect to Grafana

Import dashboard from `grafana/dashboards/mas-overview.json` on Sandbox VM.

---

## 8. SNAPSHOT STRATEGY

### Automated Snapshots

```bash
# Create cron job for VM snapshots
sudo crontab -e
# Add:
0 2 * * * /opt/mycosoft/scripts/create_vm_snapshot.sh
0 3 * * 0 /opt/mycosoft/scripts/cleanup_old_snapshots.sh
```

### Manual Snapshot Before Changes

```bash
curl -k -X POST \
  -H "Authorization: PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e" \
  "https://192.168.0.202:8006/api2/json/nodes/pve/qemu/188/snapshot" \
  -d "snapname=pre_change_$(date +%Y%m%d)"
```

---

## 9. INTEGRATION WITH SANDBOX VM

### Update Sandbox docker-compose

On Sandbox VM (192.168.0.187), update docker-compose to point to MYCA VM:

```yaml
# In docker-compose.always-on.yml
services:
  mycosoft-website:
    environment:
      - MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
```

### Configure Cross-VM Communication

Ensure firewall rules allow:
- Sandbox (187) → MYCA (188): Port 8001 (orchestrator)
- MYCA (188) → Sandbox (187): Port 8000 (MINDEX), 6379 (Redis)

---

## 10. NEXT STEPS AFTER DEPLOYMENT

### Immediate (After VM is Running)

1. [ ] Verify orchestrator health
2. [ ] Run database migration
3. [ ] Spawn 10 core agents
4. [ ] Verify agent health checks
5. [ ] Test agent-to-agent messaging

### Short-Term (This Week)

1. [ ] Build dashboard UI components
2. [ ] Connect WebSocket streaming
3. [ ] Configure all 40 agents
4. [ ] Set up Prometheus/Grafana
5. [ ] Test snapshot/restore

### Medium-Term (Next 2 Weeks)

1. [ ] Optimize agent resource allocation
2. [ ] Implement auto-scaling
3. [ ] Add advanced A2A protocols
4. [ ] Train NLM models with Qdrant
5. [ ] Connect to Innovation Roadmap systems

---

## 11. TROUBLESHOOTING

### Agent Not Starting

```bash
# Check container logs
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

---

## 12. ROLLBACK PROCEDURE

If something goes wrong:

### Rollback VM

```bash
curl -k -X POST \
  -H "Authorization: PVEAPIToken=root@pam!cursor_agent=..." \
  "https://192.168.0.202:8006/api2/json/nodes/pve/qemu/188/snapshot/<snapshot_name>/rollback"
```

### Delete and Recreate

```bash
curl -k -X DELETE \
  -H "Authorization: PVEAPIToken=root@pam!cursor_agent=..." \
  "https://192.168.0.202:8006/api2/json/nodes/pve/qemu/188"
# Then restart from Step 2
```

---

**Document Version:** 1.0.0  
**Created:** January 24, 2026  
**Status:** Ready for Execution  
**Owner:** Infrastructure Integration Agent
