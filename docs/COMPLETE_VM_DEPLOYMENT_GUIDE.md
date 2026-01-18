# Complete VM Deployment Guide for Mycosoft CREP System

**Version**: 2.0.0  
**Date**: 2026-01-16  
**Purpose**: Complete instructions for deploying Mycosoft system on a new VM with all AI tools  
**Target**: Production VM running via Cloudflare tunnel to mycosoft.com

---

## 🎯 Executive Summary

This guide provides complete instructions for cloning and deploying the entire Mycosoft system to a new virtual machine. The system includes:

- **CREP Dashboard**: Common Relevant Environmental Picture with global environmental intelligence
- **NatureOS**: Ecological data management platform
- **MINDEX**: Fungal observation database with 21,757+ observations
- **MycoBrain**: IoT device management for environmental sensors
- **MAS Orchestrator**: Multi-Agent System with 43+ n8n workflows
- **MYCA AI**: Voice-enabled AI assistant

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 8 cores | 16 cores |
| **RAM** | 32 GB | 64 GB |
| **Storage** | 500 GB SSD | 1 TB NVMe |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| **Docker** | 24.0+ | Latest |
| **Network** | 100 Mbps | 1 Gbps |

---

## 📁 Repository Structure

### Primary Codebase Location (Windows Dev Machine)

```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\
├── WEBSITE\website\           # Main Next.js application (CREP, NatureOS)
├── MAS\mycosoft-mas\         # Multi-Agent System (Orchestrator, n8n)
├── MINDEX\                    # Fungal database ETL
└── [Other repositories]
```

### Linux Production Structure

```
/opt/mycosoft/
├── website/                   # Next.js application
├── mas/                       # MAS orchestrator and n8n
├── data/                      # Persistent data volumes
│   ├── postgres/
│   ├── redis/
│   ├── qdrant/
│   ├── n8n/
│   └── mindex/
├── backups/                   # Automated backups
├── logs/                      # Centralized logs
└── config/                    # Configuration files
```

---

## 🐳 Docker Container Architecture

### Complete Container Inventory

| Stack | Container | Port | Purpose | Health Check |
|-------|-----------|------|---------|--------------|
| **Always-On** | mycosoft-website | 3000 | Main website + CREP | `/api/health` |
| **Always-On** | mindex-api | 8000 | MINDEX fungal API | `/api/health` |
| **Always-On** | mycobrain | 8003 | Device service | `/health` |
| **Always-On** | postgres | 5432 | Primary database | `pg_isready` |
| **Always-On** | redis | 6379 | Cache layer | `ping` |
| **MAS** | mas-orchestrator | 8001 | Agent orchestration | `/health` |
| **MAS** | n8n | 5678 | Workflow automation | `/healthz` |
| **MAS** | grafana | 3002 | Monitoring | `/api/health` |
| **MAS** | prometheus | 9090 | Metrics | `/-/healthy` |
| **MAS** | qdrant | 6345 | Vector database | `collections` |
| **MAS** | redis (mas) | 6390 | MAS cache | `ping` |
| **MAS** | whisper | 8765 | Speech-to-text | `/docs` |
| **MAS** | piper-tts | 10200 | Text-to-speech | - |
| **MAS** | openedai-speech | 5500 | Voice synthesis | `/v1/models` |
| **MAS** | voice-ui | 8090 | Voice interface | - |
| **MAS** | myca-dashboard | 3100 | UniFi-style dashboard | - |
| **MAS** | ollama | 11434 | LLM inference | `/api/tags` |
| **MAS** | postgres (mas) | 5433 | MAS database | `pg_isready` |
| **MINDEX** | mindex-etl | - | Data pipeline | - |
| **MINDEX** | mindex-postgres | - | MINDEX database | `pg_isready` |

### Docker Networks

| Network | Purpose |
|---------|---------|
| `mycosoft-always-on` | Website, MINDEX, MycoBrain |
| `mycosoft-mas_mas-network` | MAS services, n8n, voice |

**Critical**: Both networks must be connected for n8n integration.

---

## 🔧 Environment Variables

### Website `.env.local`

```bash
# ═══════════════════════════════════════════════════════════════════
# DATABASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
POSTGRES_URL=postgresql://mycosoft:${POSTGRES_PASSWORD}@postgres:5432/mycosoft
POSTGRES_PASSWORD=your_secure_password_here

# ═══════════════════════════════════════════════════════════════════
# CACHE & MESSAGING
# ═══════════════════════════════════════════════════════════════════
REDIS_URL=redis://mycosoft-mas-redis-1:6379

# ═══════════════════════════════════════════════════════════════════
# MINDEX INTEGRATION
# ═══════════════════════════════════════════════════════════════════
MINDEX_API_URL=http://mindex:8000
MINDEX_API_KEY=your_mindex_api_key

# ═══════════════════════════════════════════════════════════════════
# N8N INTEGRATION (Fixed 2026-01-16)
# ═══════════════════════════════════════════════════════════════════
N8N_LOCAL_URL=http://mycosoft-mas-n8n-1:5678
N8N_WEBHOOK_URL=http://mycosoft-mas-n8n-1:5678

# ═══════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════
NEXTAUTH_SECRET=your_nextauth_secret_32_chars_min
NEXTAUTH_URL=https://mycosoft.com

# ═══════════════════════════════════════════════════════════════════
# GOOGLE APIS
# ═══════════════════════════════════════════════════════════════════
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_key
GOOGLE_EARTH_ENGINE_PROJECT_ID=your_gee_project
GOOGLE_EARTH_ENGINE_PRIVATE_KEY=your_gee_private_key

# ═══════════════════════════════════════════════════════════════════
# EXTERNAL DATA APIS (Optional but recommended)
# ═══════════════════════════════════════════════════════════════════
OPENSKY_USERNAME=your_opensky_username
OPENSKY_PASSWORD=your_opensky_password
AISSTREAM_API_KEY=your_aisstream_key
FLIGHTRADAR24_API_KEY=your_fr24_key
MARINETRAFFIC_API_KEY=your_marinetraffic_key
CARBON_MAPPER_API_KEY=your_carbon_mapper_key

# ═══════════════════════════════════════════════════════════════════
# VOICE & AI SERVICES
# ═══════════════════════════════════════════════════════════════════
ELEVENLABS_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### MAS `.env`

```bash
# ═══════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════
ORCHESTRATOR_PORT=8001
ORCHESTRATOR_HOST=0.0.0.0
MAS_WORKER_COUNT=4

# ═══════════════════════════════════════════════════════════════════
# LLM SERVICES
# ═══════════════════════════════════════════════════════════════════
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b

# ═══════════════════════════════════════════════════════════════════
# VECTOR DATABASE
# ═══════════════════════════════════════════════════════════════════
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# ═══════════════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════════════
REDIS_HOST=redis
REDIS_PORT=6379

# ═══════════════════════════════════════════════════════════════════
# N8N WORKFLOWS
# ═══════════════════════════════════════════════════════════════════
N8N_HOST=n8n
N8N_PORT=5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=myca2024

# ═══════════════════════════════════════════════════════════════════
# VOICE SERVICES
# ═══════════════════════════════════════════════════════════════════
WHISPER_HOST=whisper
TTS_HOST=piper-tts
SPEECH_HOST=openedai-speech
```

---

## 🚀 Deployment Steps

### Step 1: Prepare the VM

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install required tools
sudo apt install -y git curl wget htop tmux jq

# Create directory structure
sudo mkdir -p /opt/mycosoft/{website,mas,data/{postgres,redis,qdrant,n8n,mindex},backups,logs,config}
sudo chown -R $USER:$USER /opt/mycosoft

# Create Docker networks
docker network create mycosoft-always-on
docker network create mycosoft-mas_mas-network
```

### Step 2: Clone Repositories

```bash
cd /opt/mycosoft

# Clone website repository
git clone https://github.com/mycosoft/website.git website

# Clone MAS repository
git clone https://github.com/mycosoft/mycosoft-mas.git mas
```

### Step 3: Configure Environment Files

```bash
# Copy example environment files
cp website/.env.example website/.env.local
cp mas/.env.example mas/.env

# Edit with production values
nano website/.env.local
nano mas/.env
```

### Step 4: Import Docker Images (Option A - From Backup)

If you have Docker image exports:

```bash
# Load images from tar files
docker load -i mycosoft-website.tar
docker load -i mycosoft-mas.tar
docker load -i mycosoft-mindex.tar
```

### Step 4: Build from Source (Option B)

```bash
# Build website
cd /opt/mycosoft/website
docker-compose build website --no-cache

# MAS uses pre-built images, no build needed
```

### Step 5: Start Services (Critical Order)

```bash
# 1. Start MAS stack FIRST (contains n8n and Redis)
cd /opt/mycosoft/mas
docker-compose up -d

# Wait for n8n to be ready
sleep 30
curl -s http://localhost:5678/healthz

# 2. Start Always-On stack SECOND
cd /opt/mycosoft/website
docker-compose -f docker-compose.always-on.yml up -d

# 3. Verify all containers are running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Step 6: Connect Networks for n8n Integration

```bash
# Connect n8n and redis to always-on network
docker network connect mycosoft-always-on mycosoft-mas-n8n-1
docker network connect mycosoft-always-on mycosoft-mas-redis-1

# Verify connections
docker network inspect mycosoft-always-on | jq '.[0].Containers'
```

### Step 7: Verify Deployment

```bash
# Test all health endpoints
curl http://localhost:3000/api/health        # Website
curl http://localhost:8000/api/health        # MINDEX
curl http://localhost:8001/health            # MAS Orchestrator
curl http://localhost:5678/healthz           # n8n
curl http://localhost:3000/api/natureos/n8n  # n8n integration

# Test CREP APIs
curl "http://localhost:3000/api/crep/fungal?limit=5" | jq '.meta.total'
curl "http://localhost:3000/api/oei/opensky?limit=5" | jq '.total'
```

---

## 🌐 Cloudflare Tunnel Setup

### Install Cloudflared

```bash
# Download and install
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Login to Cloudflare
cloudflared tunnel login
```

### Create Tunnel

```bash
# Create tunnel
cloudflared tunnel create mycosoft

# Configure tunnel
cat > /etc/cloudflared/config.yml << 'EOF'
tunnel: <TUNNEL_UUID>
credentials-file: /root/.cloudflared/<TUNNEL_UUID>.json

ingress:
  # Main website
  - hostname: mycosoft.com
    service: http://localhost:3000
  
  # CREP Dashboard
  - hostname: crep.mycosoft.com
    service: http://localhost:3000
  
  # n8n Workflows
  - hostname: n8n.mycosoft.com
    service: http://localhost:5678
  
  # Grafana Monitoring
  - hostname: grafana.mycosoft.com
    service: http://localhost:3002
  
  # MYCA Dashboard
  - hostname: myca.mycosoft.com
    service: http://localhost:3100
  
  # Catch-all
  - service: http_status:404
EOF

# Route DNS
cloudflared tunnel route dns mycosoft mycosoft.com
cloudflared tunnel route dns mycosoft crep.mycosoft.com
cloudflared tunnel route dns mycosoft n8n.mycosoft.com
cloudflared tunnel route dns mycosoft grafana.mycosoft.com
cloudflared tunnel route dns mycosoft myca.mycosoft.com

# Install as service
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### Verify Tunnel

```bash
# Check tunnel status
cloudflared tunnel info mycosoft
systemctl status cloudflared

# Test external access
curl https://mycosoft.com/api/health
```

---

## 🤖 AI Tools Integration

### Cursor IDE Setup

1. Install Cursor from https://cursor.sh
2. Open `/opt/mycosoft/` as workspace
3. Configure MCP servers in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "Notion": {
      "command": "npx",
      "args": ["@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer ntn_xxx\", \"Notion-Version\": \"2022-06-28\"}"
      }
    },
    "cursor-browser-extension": {
      "socketPath": "~/.cursor-mcp-browser"
    }
  }
}
```

### Claude Desktop Setup

1. Install Claude Desktop
2. Configure MCP tools for system access
3. Add custom instructions for Mycosoft context

### ChatGPT Desktop Setup

1. Install ChatGPT Desktop
2. Enable advanced data analysis
3. Configure for code review tasks

---

## 📊 n8n Workflows (43+ Active)

### Workflow Categories

| Category | Count | Purpose |
|----------|-------|---------|
| **MYCA AI Assistant** | 8 | Voice chat, text chat, routing |
| **MycoBrain Telemetry** | 2 | Device data ingestion |
| **MINDEX Pipeline** | 2 | Fungal data ETL |
| **Space Weather** | 6 | Solar activity, geomagnetic storms |
| **Defense Connector** | 1 | Security integrations |
| **Operations** | 5 | System monitoring, alerts |
| **Speech & Voice** | 5 | STT, TTS pipelines |
| **Integration & Routing** | 8+ | Zapier MCP, webhooks |

### Import Workflows

```bash
# Workflows are in the n8n volume
# Access n8n UI at http://localhost:5678
# Import from: mas/n8n/workflows/
```

### Key Webhook Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /webhook/chat` | Text chat with MYCA |
| `POST /webhook/voice-chat` | Voice chat pipeline |
| `POST /webhook/myca-command` | MAS command router |
| `POST /webhook/device-telemetry` | Device data ingestion |

---

## 🔒 Security Hardening

### Firewall Configuration

```bash
# Install UFW
sudo apt install ufw -y

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow Cloudflare IPs only for HTTP/HTTPS
# (In practice, ports 80/443 should not be exposed directly)

# Enable firewall
sudo ufw enable
```

### SSL/TLS Configuration

Cloudflare tunnel provides end-to-end encryption. For internal services:

```bash
# Generate self-signed certs for internal services
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/mycosoft/config/ssl/private.key \
  -out /opt/mycosoft/config/ssl/certificate.crt
```

---

## 💾 Backup Strategy

### Automated Backup Script

```bash
#!/bin/bash
# /opt/mycosoft/scripts/backup.sh

BACKUP_DIR="/opt/mycosoft/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL databases
docker exec mycosoft-postgres pg_dumpall -U mycosoft > $BACKUP_DIR/postgres_$DATE.sql
docker exec mas-postgres pg_dumpall -U mycosoft > $BACKUP_DIR/mas_postgres_$DATE.sql

# Backup Redis
docker exec mycosoft-redis redis-cli BGSAVE

# Backup n8n workflows
docker exec mycosoft-mas-n8n-1 n8n export:workflow --all --output=$BACKUP_DIR/n8n_workflows_$DATE.json

# Backup Docker volumes
docker run --rm -v mycosoft_data:/data -v $BACKUP_DIR:/backup alpine \
  tar czf /backup/volumes_$DATE.tar.gz /data

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Cron Schedule

```bash
# Add to crontab
0 2 * * * /opt/mycosoft/scripts/backup.sh >> /var/log/mycosoft-backup.log 2>&1
```

---

## 📈 Monitoring & Alerts

### Grafana Dashboards

- **System Overview**: CPU, Memory, Disk, Network
- **Container Health**: Docker container metrics
- **API Performance**: Response times, error rates
- **CREP Data**: Event counts, data freshness

### Prometheus Alerts

```yaml
# /opt/mycosoft/config/prometheus/alerts.yml
groups:
  - name: mycosoft
    rules:
      - alert: ContainerDown
        expr: up{job="docker"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.container }} is down"
      
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.service }}"
```

---

## 🛠️ Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker logs <container_name> --tail 100

# Check resource usage
docker stats

# Restart container
docker-compose restart <service>
```

#### n8n Connection Failed
```bash
# Verify network connections
docker network inspect mycosoft-always-on | grep -A5 n8n

# Test from website container
docker exec mycosoft-website curl http://mycosoft-mas-n8n-1:5678/healthz
```

#### Database Connection Failed
```bash
# Check database status
docker exec mycosoft-postgres pg_isready

# Reset database
docker-compose down -v
docker-compose up -d
```

#### MINDEX ETL Unhealthy
```bash
# Check scheduler error
docker logs mycosoft-always-on-mindex-etl-1 --tail 50

# Known issue: Type comparison error in scheduler.py
# Fix: Update scheduler.py line 95
```

---

## 📚 Documentation Index

### MAS Repository Docs
| Document | Purpose |
|----------|---------|
| `docs/SERVER_MIGRATION_MASTER_GUIDE.md` | Master migration reference |
| `docs/N8N_INTEGRATION_GUIDE.md` | n8n workflow documentation |
| `docs/CREP_DATA_SOURCE_APIS.md` | External API reference |

### Website Repository Docs
| Document | Purpose |
|----------|---------|
| `docs/CREP_INFRASTRUCTURE_DEPLOYMENT.md` | CREP deployment guide |
| `docs/PORT_ASSIGNMENTS.md` | Port reference |
| `docs/SYSTEM_ARCHITECTURE.md` | Architecture overview |

---

## ✅ Go-Live Checklist

- [ ] All containers healthy (`docker ps`)
- [ ] All health endpoints responding
- [ ] CREP dashboard loading at https://mycosoft.com/dashboard/crep
- [ ] Fungal markers displaying on map
- [ ] Event markers clickable with popups
- [ ] Aircraft/Vessel/Satellite data loading
- [ ] n8n workflows active
- [ ] Cloudflare tunnel connected
- [ ] SSL certificates valid
- [ ] Backups configured
- [ ] Monitoring alerts set
- [ ] DNS propagated

---

## 📞 Support

For issues, check:
1. Container logs: `docker logs <container>`
2. Grafana dashboards: http://localhost:3002
3. n8n execution history: http://localhost:5678

---

*Generated by MYCA Integration System - 2026-01-16*
