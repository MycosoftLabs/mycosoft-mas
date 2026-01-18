#!/bin/bash
# MycoBrain Bridge Configuration Script for VM 103
# Run this on the VM after SSH: ssh mycosoft@192.168.0.187

echo "=========================================="
echo "MycoBrain Bridge Configuration"
echo "=========================================="
echo ""

# Step 1: Test connectivity to Windows MycoBrain service
echo "[1/4] Testing connectivity to Windows MycoBrain..."
if curl -s http://192.168.0.172:8003/health | grep -q "ok"; then
    echo "  âœ… Windows MycoBrain service is reachable!"
    curl -s http://192.168.0.172:8003/health | jq .
else
    echo "  âŒ Cannot reach Windows MycoBrain service!"
    echo "  Check Windows firewall rule for port 8003"
    exit 1
fi

echo ""
echo "[2/4] Finding docker-compose configuration..."
cd /opt/mycosoft 2>/dev/null || cd ~/mycosoft 2>/dev/null || cd /home/mycosoft 2>/dev/null

if [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
elif [ -f "docker-compose.always-on.yml" ]; then
    COMPOSE_FILE="docker-compose.always-on.yml"
else
    echo "  âŒ No docker-compose file found"
    ls -la
    exit 1
fi
echo "  Found: $COMPOSE_FILE"

echo ""
echo "[3/4] Updating MYCOBRAIN_SERVICE_URL..."
# Create or update .env file
if grep -q "MYCOBRAIN_SERVICE_URL" .env 2>/dev/null; then
    sed -i 's|MYCOBRAIN_SERVICE_URL=.*|MYCOBRAIN_SERVICE_URL=http://192.168.0.172:8003|' .env
    echo "  Updated existing MYCOBRAIN_SERVICE_URL in .env"
else
    echo "MYCOBRAIN_SERVICE_URL=http://192.168.0.172:8003" >> .env
    echo "  Added MYCOBRAIN_SERVICE_URL to .env"
fi

echo ""
echo "[4/4] Restarting website container..."
docker-compose -f $COMPOSE_FILE up -d --force-recreate mycosoft-website 2>/dev/null || \
docker compose -f $COMPOSE_FILE up -d --force-recreate mycosoft-website

echo ""
echo "=========================================="
echo "Configuration Complete!"
echo "=========================================="
echo "Test: https://sandbox.mycosoft.com/api/mycobrain"