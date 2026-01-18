# Mycosoft Stack Deployment Guide

*Created: January 17, 2026*  
*For: VM 103 (mycosoft-sandbox) - Ubuntu Server 24.04.2 LTS*

---

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone Repositories](#2-clone-repositories)
3. [Environment Configuration](#3-environment-configuration)
4. [Deploy Always-On Stack](#4-deploy-always-on-stack)
5. [Deploy MAS Stack](#5-deploy-mas-stack)
6. [Deploy Website](#6-deploy-website)
7. [Network Configuration](#7-network-configuration)
8. [Health Verification](#8-health-verification)
9. [Startup Order & Scripts](#9-startup-order--scripts)

---

## 1. Prerequisites

Ensure the following are installed and working:

```bash
# Verify Docker
docker --version      # Expected: 24.x+
docker compose version  # Expected: v2.x+

# Verify directory structure
ls -la /opt/mycosoft/
```

---

## 2. Clone Repositories

### Clone from GitHub

```bash
cd /opt/mycosoft

# Clone MAS repository
git clone https://github.com/MYCOSOFT/mycosoft-mas.git mas
# OR if private repository
git clone git@github.com:MYCOSOFT/mycosoft-mas.git mas

# Clone Website repository  
git clone https://github.com/MYCOSOFT/mycosoft-website.git website
# OR if private repository
git clone git@github.com:MYCOSOFT/mycosoft-website.git website
```

### Alternative: Transfer from Windows

If repositories aren't on GitHub, transfer from Windows:

```powershell
# From Windows PowerShell
# Option 1: SCP
scp -r "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\*" mycosoft@192.168.0.103:/opt/mycosoft/mas/
scp -r "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\*" mycosoft@192.168.0.103:/opt/mycosoft/website/

# Option 2: rsync (faster for large transfers)
rsync -avz --progress "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas/" mycosoft@192.168.0.103:/opt/mycosoft/mas/
rsync -avz --progress "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website/" mycosoft@192.168.0.103:/opt/mycosoft/website/
```

---

## 3. Environment Configuration

### Create .env Files

#### MAS Stack Environment

```bash
cat > /opt/mycosoft/mas/.env << 'EOF'
# Database
POSTGRES_USER=mycosoft
POSTGRES_PASSWORD=<GENERATE_STRONG_PASSWORD>
POSTGRES_DB=mycosoft_mas
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379
REDIS_HOST=redis
REDIS_PORT=6379

# n8n
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<GENERATE_STRONG_PASSWORD>
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
WEBHOOK_URL=https://n8n.mycosoft.com/
N8N_ENCRYPTION_KEY=<GENERATE_32_CHAR_KEY>

# MINDEX
MINDEX_API_URL=http://mindex-api:8000
MINDEX_DATABASE_URL=postgresql://mycosoft:<PASSWORD>@postgres:5432/mindex

# MycoBrain
MYCOBRAIN_API_URL=http://mycobrain:8003
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
ANTHROPIC_API_KEY=<YOUR_ANTHROPIC_API_KEY>

# MinIO (Object Storage)
MINIO_ROOT_USER=mycosoft
MINIO_ROOT_PASSWORD=<GENERATE_STRONG_PASSWORD>
MINIO_ENDPOINT=minio:9000

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<GENERATE_STRONG_PASSWORD>
GF_SERVER_ROOT_URL=https://grafana.mycosoft.com

# General
NODE_ENV=production
LOG_LEVEL=info
EOF
```

#### Website Environment

```bash
cat > /opt/mycosoft/website/.env.local << 'EOF'
# Next.js
NEXT_PUBLIC_API_URL=https://api.mycosoft.com
NEXT_PUBLIC_SITE_URL=https://mycosoft.com

# Internal API URLs (Docker network)
N8N_LOCAL_URL=http://mycosoft-mas-n8n-1:5678
REDIS_URL=redis://mycosoft-mas-redis-1:6379
MINDEX_API_URL=http://mindex-api:8000
MYCOBRAIN_URL=http://mycobrain:8003

# CREP Data Sources
FLIGHTRADAR24_API_KEY=<YOUR_KEY>
AISSTREAM_API_KEY=<YOUR_KEY>
CELESTRAK_API_URL=https://celestrak.org

# Authentication
NEXTAUTH_SECRET=<GENERATE_32_CHAR_SECRET>
NEXTAUTH_URL=https://mycosoft.com

# Database
DATABASE_URL=postgresql://mycosoft:<PASSWORD>@postgres:5432/website

# Cache
CACHE_TTL=300
EOF
```

### Generate Secure Passwords

```bash
# Generate random passwords
openssl rand -base64 32  # For database passwords
openssl rand -hex 16     # For encryption keys
```

---

## 4. Deploy Always-On Stack

The Always-On stack includes core infrastructure that runs 24/7.

### Docker Compose File Location

```bash
cd /opt/mycosoft/mas
```

### Start Always-On Services

```bash
# Build and start
docker compose -f docker-compose.always-on.yml up -d --build

# View logs
docker compose -f docker-compose.always-on.yml logs -f
```

### Always-On Services

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache/queue |
| mindex-api | 8000 | Fungal intelligence API |
| mindex-etl | - | ETL data pipeline |
| grafana | 3002 | Monitoring dashboard |
| prometheus | 9090 | Metrics collection |

### Verify Always-On Stack

```bash
# Check container status
docker compose -f docker-compose.always-on.yml ps

# Health checks
curl http://localhost:8000/health  # MINDEX API
curl http://localhost:3002/api/health  # Grafana
curl http://localhost:9090/-/healthy  # Prometheus
```

---

## 5. Deploy MAS Stack

The MAS (Mycosoft Agent System) stack includes AI agents and orchestration.

### Start MAS Services

```bash
cd /opt/mycosoft/mas

# Build and start
docker compose up -d --build

# View logs
docker compose logs -f
```

### MAS Services

| Service | Port | Description |
|---------|------|-------------|
| n8n | 5678 | Workflow automation |
| mas-orchestrator | 8001 | Agent orchestration |
| mycobrain | 8003 | AI reasoning engine |
| myca-agent | 8004 | Myca AI assistant |

### Verify MAS Stack

```bash
# Check container status
docker compose ps

# Health checks
curl http://localhost:5678/healthz  # n8n
curl http://localhost:8001/health   # Orchestrator
curl http://localhost:8003/health   # MycoBrain
```

---

## 6. Deploy Website

### Build and Start Website

```bash
cd /opt/mycosoft/website

# Install dependencies (if needed for build)
# npm install

# Build and start with Docker
docker compose up -d --build

# View logs
docker compose logs -f website
```

### Website Services

| Service | Port | Description |
|---------|------|-------------|
| website | 3000 | Next.js application |
| crep-aircraft | 8010 | Aircraft data collector |
| crep-vessel | 8011 | Vessel data collector |
| crep-satellite | 8012 | Satellite data collector |

### Verify Website

```bash
# Health check
curl http://localhost:3000/api/health

# Check CREP collectors
curl http://localhost:8010/health  # Aircraft
curl http://localhost:8011/health  # Vessel
curl http://localhost:8012/health  # Satellite
```

---

## 7. Network Configuration

### Connect Networks

The website needs to communicate with MAS services:

```bash
# Connect website to MAS network
docker network connect mycosoft-mas_mas-network mycosoft-website-website-1

# Or connect MAS services to Always-On network
docker network connect mycosoft-always-on mycosoft-mas-n8n-1
docker network connect mycosoft-always-on mycosoft-mas-redis-1
```

### Verify Network Connectivity

```bash
# From website container, test n8n connection
docker exec mycosoft-website-website-1 curl -s http://mycosoft-mas-n8n-1:5678/healthz

# List all networks
docker network ls

# Inspect network
docker network inspect mycosoft-always-on
```

---

## 8. Health Verification

### Master Health Check Script

```bash
cat > /opt/mycosoft/scripts/health-check.sh << 'EOF'
#!/bin/bash

echo "=========================================="
echo "Mycosoft System Health Check"
echo "$(date)"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check_service() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url")
    if [ "$response" = "200" ] || [ "$response" = "204" ]; then
        echo -e "[$GREEN✓$NC] $name"
        return 0
    else
        echo -e "[$RED✗$NC] $name (HTTP $response)"
        return 1
    fi
}

echo -e "\n--- Core Infrastructure ---"
check_service "PostgreSQL" "http://localhost:5432" 2>/dev/null || echo "  (direct check not available)"
check_service "Redis" "http://localhost:6379" 2>/dev/null || echo "  (direct check not available)"

echo -e "\n--- Always-On Stack ---"
check_service "MINDEX API" "http://localhost:8000/health"
check_service "Grafana" "http://localhost:3002/api/health"
check_service "Prometheus" "http://localhost:9090/-/healthy"

echo -e "\n--- MAS Stack ---"
check_service "n8n" "http://localhost:5678/healthz"
check_service "MAS Orchestrator" "http://localhost:8001/health"
check_service "MycoBrain" "http://localhost:8003/health"

echo -e "\n--- Website Stack ---"
check_service "Website" "http://localhost:3000/api/health"
check_service "CREP Aircraft" "http://localhost:8010/health"
check_service "CREP Vessel" "http://localhost:8011/health"
check_service "CREP Satellite" "http://localhost:8012/health"

echo -e "\n--- Container Status ---"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20

echo -e "\n--- Resource Usage ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -15

echo -e "\n=========================================="
echo "Health check complete"
echo "=========================================="
EOF

chmod +x /opt/mycosoft/scripts/health-check.sh
```

### Run Health Check

```bash
/opt/mycosoft/scripts/health-check.sh
```

---

## 9. Startup Order & Scripts

### Startup Script

```bash
cat > /opt/mycosoft/scripts/start-all.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting Mycosoft Stack..."
echo "=========================="

# 1. Start Always-On stack first (databases, core services)
echo "Starting Always-On stack..."
cd /opt/mycosoft/mas
docker compose -f docker-compose.always-on.yml up -d

# Wait for databases to be ready
echo "Waiting for databases..."
sleep 10

# 2. Start MAS stack (n8n, agents)
echo "Starting MAS stack..."
docker compose up -d

# Wait for n8n to be ready
echo "Waiting for n8n..."
sleep 5

# 3. Start Website stack
echo "Starting Website stack..."
cd /opt/mycosoft/website
docker compose up -d

# 4. Connect networks
echo "Connecting networks..."
docker network connect mycosoft-always-on mycosoft-mas-n8n-1 2>/dev/null || true
docker network connect mycosoft-always-on mycosoft-mas-redis-1 2>/dev/null || true

echo ""
echo "All services started!"
echo "Run health check: /opt/mycosoft/scripts/health-check.sh"
EOF

chmod +x /opt/mycosoft/scripts/start-all.sh
```

### Shutdown Script

```bash
cat > /opt/mycosoft/scripts/stop-all.sh << 'EOF'
#!/bin/bash

echo "Stopping Mycosoft Stack..."
echo "=========================="

# Stop in reverse order
cd /opt/mycosoft/website
docker compose down

cd /opt/mycosoft/mas
docker compose down
docker compose -f docker-compose.always-on.yml down

echo "All services stopped."
EOF

chmod +x /opt/mycosoft/scripts/stop-all.sh
```

### Systemd Service (Auto-start on Boot)

```bash
sudo tee /etc/systemd/system/mycosoft.service << 'EOF'
[Unit]
Description=Mycosoft Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=mycosoft
WorkingDirectory=/opt/mycosoft
ExecStart=/opt/mycosoft/scripts/start-all.sh
ExecStop=/opt/mycosoft/scripts/stop-all.sh
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable mycosoft.service
```

---

## 🎯 Next Steps

1. Verify all services are running: `/opt/mycosoft/scripts/health-check.sh`
2. Configure Cloudflare Tunnel: See **[CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)**
3. Import n8n workflows
4. Test CREP dashboard

---

*Document Version: 1.0*  
*Last Updated: January 17, 2026*
