#!/bin/bash
# Setup script for myca-api VM (192.168.20.10)
# Run after vm_setup_common.sh

set -e

echo "=================================================="
echo "  MYCA API VM Setup"
echo "=================================================="

VM_IP="192.168.20.10"
DB_IP="192.168.20.12"
NAS_PATH="/mnt/mycosoft"

# Verify NAS mount
echo "[1/8] Verifying NAS mount..."
if ! mountpoint -q $NAS_PATH; then
    echo "ERROR: NAS not mounted at $NAS_PATH"
    exit 1
fi

# Install Python 3.11
echo "[2/8] Installing Python 3.11..."
apt install -y python3.11 python3.11-venv python3-pip

# Create directories
echo "[3/8] Creating directories..."
mkdir -p $NAS_PATH/agents/{cycles,insights,workloads,wisdom}
mkdir -p $NAS_PATH/knowledge/{mindex,encyclopedia,embeddings}
mkdir -p /opt/myca
mkdir -p /var/log/myca

# Clone repository
echo "[4/8] Cloning MYCA repository..."
if [ ! -d /opt/myca/.git ]; then
    git clone https://github.com/MycosoftLabs/mycosoft-mas.git /opt/myca
else
    cd /opt/myca && git pull
fi

# Create Docker network
echo "[5/8] Creating Docker network..."
docker network create myca-network 2>/dev/null || true

# Create docker-compose for API services
echo "[6/8] Creating docker-compose.yml..."
cat > /opt/myca/docker-compose.api.yml << 'EOF'
version: '3.8'

services:
  myca-api:
    build:
      context: .
      dockerfile: Dockerfile.orchestrator
    container_name: myca-api
    restart: always
    environment:
      - MAS_ENV=production
      - DATABASE_URL=postgresql://mas:${POSTGRES_PASSWORD}@192.168.20.12:5432/mas
      - REDIS_URL=redis://192.168.20.12:6379
      - QDRANT_URL=http://192.168.20.12:6333
      - NAS_STORAGE_PATH=/mnt/mycosoft
      - LLM_BASE_URL=${LLM_BASE_URL:-http://192.168.0.100:11434}
    volumes:
      - /mnt/mycosoft:/mnt/mycosoft
      - /var/log/myca:/var/log/myca
    ports:
      - "8001:8001"
    networks:
      - myca-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mindex:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: myca-mindex
    restart: always
    environment:
      - DATABASE_URL=postgresql://mindex:${MINDEX_PASSWORD}@192.168.20.12:5432/mindex
      - QDRANT_URL=http://192.168.20.12:6333
    volumes:
      - /mnt/mycosoft/knowledge:/mnt/mycosoft/knowledge
    ports:
      - "8000:8000"
    networks:
      - myca-network

  natureos:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: myca-natureos
    restart: always
    environment:
      - DATABASE_URL=postgresql://natureos:${NATUREOS_PASSWORD}@192.168.20.12:5432/natureos
    ports:
      - "8002:8002"
    networks:
      - myca-network

  n8n:
    image: n8nio/n8n:latest
    container_name: myca-n8n
    restart: always
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=https://webhooks.mycosoft.com
    volumes:
      - /mnt/mycosoft/n8n:/home/node/.n8n
    ports:
      - "5678:5678"
    networks:
      - myca-network

  dashboard:
    build:
      context: ./unifi-dashboard
      dockerfile: Dockerfile
    container_name: myca-dashboard
    restart: always
    environment:
      - API_URL=http://myca-api:8001
    ports:
      - "3100:3100"
    networks:
      - myca-network

networks:
  myca-network:
    external: true
EOF

# Create environment file
echo "[7/8] Creating environment file..."
cat > /etc/myca/api.env << EOF
# Database connections
POSTGRES_PASSWORD=CHANGE_ME
MINDEX_PASSWORD=CHANGE_ME
NATUREOS_PASSWORD=CHANGE_ME

# n8n
N8N_USER=admin
N8N_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)

# LLM (mycocomp GPU)
LLM_BASE_URL=http://192.168.0.100:11434

# JWT
JWT_SECRET=$(openssl rand -base64 32)

# Environment
MAS_ENV=production
DEBUG_MODE=false
EOF
chmod 600 /etc/myca/api.env

# Install cloudflared
echo "[8/8] Installing cloudflared..."
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared.deb
rm cloudflared.deb

# Create systemd service
cat > /etc/systemd/system/myca-api.service << 'EOF'
[Unit]
Description=MYCA API Services
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/myca
EnvironmentFile=/etc/myca/api.env
ExecStart=/usr/bin/docker compose -f docker-compose.api.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.api.yml down
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable myca-api

echo ""
echo "=================================================="
echo "  API VM Setup Complete!"
echo "=================================================="
echo ""
echo "  IMPORTANT: Update /etc/myca/api.env with real passwords!"
echo ""
echo "  Next steps:"
echo "  1. Edit /etc/myca/api.env with database passwords"
echo "  2. Run: cloudflared tunnel login"
echo "  3. Create tunnel: cloudflared tunnel create mycosoft-tunnel"
echo "  4. Copy config: cp /opt/myca/config/cloudflared/config.yml /etc/cloudflared/"
echo "  5. Start services: systemctl start myca-api"
echo ""
echo "  Services will be available at:"
echo "    MAS API: http://$VM_IP:8001"
echo "    MINDEX: http://$VM_IP:8000"
echo "    NatureOS: http://$VM_IP:8002"
echo "    n8n: http://$VM_IP:5678"
echo "    Dashboard: http://$VM_IP:3100"
echo ""
