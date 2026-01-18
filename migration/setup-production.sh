#!/bin/bash
# Complete Production Setup Script
# Run this on VM1 after codebase transfer

set -e

echo "=========================================="
echo "Mycosoft Production Setup"
echo "=========================================="

cd /opt/mycosoft

# Check if .env exists
if [ ! -f .env ]; then
    echo "[1/6] Creating .env file from template..."
    cp env.example .env 2>/dev/null || {
        cat > .env << 'EOF'
# Database
POSTGRES_PASSWORD=CHANGE_THIS_SECURE_PASSWORD
DATABASE_URL=postgresql://mas:CHANGE_THIS_SECURE_PASSWORD@postgres:5432/mas

# Redis
REDIS_URL=redis://redis:6379/0

# Qdrant
QDRANT_URL=http://qdrant:6333

# Grafana
GRAFANA_PASSWORD=CHANGE_THIS

# n8n
N8N_USER=admin
N8N_PASSWORD=CHANGE_THIS

# API Keys (add your keys)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here

# Environment
MAS_ENV=production
DEBUG_MODE=false
LOG_LEVEL=INFO
EOF
    }
    echo "⚠️  Please edit .env file with your passwords and API keys!"
    read -p "Press Enter after editing .env file..."
fi

# Copy production docker-compose
echo "[2/6] Setting up Docker Compose..."
if [ -f migration/docker-compose.prod.yml ]; then
    cp migration/docker-compose.prod.yml docker-compose.prod.yml
    echo "Production docker-compose.yml ready"
else
    echo "ERROR: docker-compose.prod.yml not found in migration/"
    exit 1
fi

# Start infrastructure services first
echo "[3/6] Starting infrastructure services..."
docker-compose -f docker-compose.prod.yml up -d postgres redis qdrant

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 15

# Build application images
echo "[4/6] Building application images..."
docker-compose -f docker-compose.prod.yml build mas-orchestrator website mycobrain-service

# Start all services
echo "[5/6] Starting all services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services
echo "Waiting for services to start..."
sleep 20

# Run health check
echo "[6/6] Running health check..."
chmod +x migration/health-check.sh
./migration/health-check.sh

echo ""
echo "=========================================="
echo "Production setup completed!"
echo "=========================================="
echo ""
echo "Services should now be running."
echo "Check status: docker-compose -f docker-compose.prod.yml ps"
echo "View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "Health check: ./migration/health-check.sh"
