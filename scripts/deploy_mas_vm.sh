#!/bin/bash
# MAS VM Deployment Script - Jan 26, 2026
# Run this on the MAS VM (192.168.0.188) to deploy latest code

set -e

echo "=== MAS VM Deployment Script ==="
echo "Date: $(date)"

# Navigate to MAS directory
cd /opt/mycosoft/mas || { echo "ERROR: /opt/mycosoft/mas not found"; exit 1; }

# Pull latest code
echo "Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

# Check if running in Docker or systemd
if docker ps | grep -q myca-orchestrator; then
    echo "Restarting Docker container..."
    docker-compose pull myca-orchestrator 2>/dev/null || true
    docker-compose up -d myca-orchestrator
elif systemctl is-active --quiet myca-orchestrator; then
    echo "Restarting systemd service..."
    sudo systemctl restart myca-orchestrator
else
    echo "Starting orchestrator directly..."
    # Kill existing if running
    pkill -f "orchestrator_service" 2>/dev/null || true
    sleep 2
    
    # Start with nohup
    cd /opt/mycosoft/mas
    nohup python3 -m mycosoft_mas.core.orchestrator_service > /var/log/myca-orchestrator.log 2>&1 &
    echo "Started orchestrator (PID: $!)"
fi

# Wait and verify
sleep 3
echo "Verifying orchestrator..."
curl -s http://localhost:8001/health && echo " - Health OK"
curl -s http://localhost:8001/connections && echo " - Connections endpoint OK"

echo "=== Deployment Complete ==="
