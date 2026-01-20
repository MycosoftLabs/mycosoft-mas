#!/bin/bash
# ============================================================================
# Mycosoft VM Setup Commands
# Run these commands on the VM (192.168.0.187) after SSH login
# ============================================================================

echo "=== Mycosoft VM Setup ==="
echo ""

# 1. Set NEXTAUTH_SECRET
echo "Step 1: Setting NEXTAUTH_SECRET..."
NEXTAUTH_SECRET="hMG8sSNcsxX/W7DXUxsDpJ7m0VxPRCoNLWnrxUK7pLs="

# Find the .env file location
ENV_FILE=""
if [ -f "/home/mycosoft/mycosoft/mas/.env" ]; then
    ENV_FILE="/home/mycosoft/mycosoft/mas/.env"
elif [ -f "/opt/mycosoft/mas/.env" ]; then
    ENV_FILE="/opt/mycosoft/mas/.env"
elif [ -f "/home/mycosoft/.env" ]; then
    ENV_FILE="/home/mycosoft/.env"
else
    echo "No .env file found. Creating one..."
    ENV_FILE="/home/mycosoft/mycosoft/mas/.env"
    mkdir -p "$(dirname "$ENV_FILE")"
    touch "$ENV_FILE"
fi

echo "Using env file: $ENV_FILE"

# Check if NEXTAUTH_SECRET already exists
if grep -q "NEXTAUTH_SECRET" "$ENV_FILE" 2>/dev/null; then
    echo "NEXTAUTH_SECRET already exists in $ENV_FILE"
    echo "Current value:"
    grep "NEXTAUTH_SECRET" "$ENV_FILE"
else
    echo "Adding NEXTAUTH_SECRET..."
    echo "" >> "$ENV_FILE"
    echo "# NextAuth Secret (generated Jan 20, 2026)" >> "$ENV_FILE"
    echo "NEXTAUTH_SECRET=$NEXTAUTH_SECRET" >> "$ENV_FILE"
    echo "[OK] NEXTAUTH_SECRET added"
fi

# 2. Check current VM specs
echo ""
echo "Step 2: Current VM Specifications"
echo "=================================="
echo "CPU Cores: $(nproc)"
echo "Total RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Disk Usage:"
df -h / | tail -1

# 3. Check Docker containers
echo ""
echo "Step 3: Docker Container Status"
echo "================================"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not running or permission denied"

# 4. Check MycoBrain health
echo ""
echo "Step 4: Service Health Checks"
echo "============================="
curl -sf http://localhost:3000/api/health >/dev/null 2>&1 && echo "[OK] Website (3000)" || echo "[FAIL] Website (3000)"
curl -sf http://localhost:8000/health >/dev/null 2>&1 && echo "[OK] MINDEX API (8000)" || echo "[FAIL] MINDEX API (8000)"
curl -sf http://localhost:8003/health >/dev/null 2>&1 && echo "[OK] MycoBrain (8003)" || echo "[FAIL] MycoBrain (8003)"

# 5. Check cloudflared
echo ""
echo "Step 5: Cloudflared Status"
echo "=========================="
systemctl is-active --quiet cloudflared && echo "[OK] Cloudflared is running" || echo "[FAIL] Cloudflared not running"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. If VM specs need upgrading, shutdown and modify in Proxmox"
echo "2. Rebuild website container: docker compose -f docker-compose.always-on.yml up -d --build mycosoft-website"
echo "3. Clear Cloudflare cache"
