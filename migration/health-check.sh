#!/bin/bash
# Production Health Check Script
# Run this on VM1 to verify all services

set -e

echo "=========================================="
echo "Mycosoft Production Health Check"
echo "Date: $(date)"
echo "=========================================="
echo ""

# Check Docker
echo "=== Docker Status ==="
if command -v docker &> /dev/null; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
    echo ""
else
    echo "ERROR: Docker not installed"
    exit 1
fi

# Check Service Endpoints
echo "=== Service Health Endpoints ==="

check_endpoint() {
    local name=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "✅ $name: HEALTHY ($url)"
        return 0
    else
        echo "❌ $name: UNHEALTHY ($url)"
        return 1
    fi
}

check_endpoint "MAS Orchestrator" "http://localhost:8001/health"
check_endpoint "Website" "http://localhost:3000"
check_endpoint "MycoBrain Service" "http://localhost:8003/health"
check_endpoint "Prometheus" "http://localhost:9090/-/healthy"
check_endpoint "Grafana" "http://localhost:3002/api/health"
check_endpoint "n8n" "http://localhost:5678/healthz"
check_endpoint "Qdrant" "http://localhost:6333/health"

echo ""

# Check Database
echo "=== Database Status ==="
if docker ps | grep -q mycosoft-postgres; then
    DB_CHECK=$(docker exec mycosoft-postgres psql -U mas -d mas -t -c "SELECT COUNT(*) FROM information_schema.tables;" 2>/dev/null)
    if [ -n "$DB_CHECK" ]; then
        echo "✅ PostgreSQL: Connected ($DB_CHECK tables)"
    else
        echo "❌ PostgreSQL: Connection failed"
    fi
else
    echo "❌ PostgreSQL: Container not running"
fi

if docker ps | grep -q mycosoft-redis; then
    REDIS_CHECK=$(docker exec mycosoft-redis redis-cli PING 2>/dev/null)
    if [ "$REDIS_CHECK" = "PONG" ]; then
        echo "✅ Redis: Connected"
    else
        echo "❌ Redis: Connection failed"
    fi
else
    echo "❌ Redis: Container not running"
fi

echo ""

# Check Cloudflare Tunnel
echo "=== Cloudflare Tunnel ==="
if systemctl is-active --quiet cloudflared; then
    echo "✅ Cloudflare Tunnel: Running"
    sudo systemctl status cloudflared --no-pager | head -3
else
    echo "❌ Cloudflare Tunnel: Not running"
fi

echo ""

# Check Disk Space
echo "=== Disk Usage ==="
df -h / | tail -1
df -h /mnt/mycosoft-nas 2>/dev/null | tail -1 || echo "NAS not mounted"

echo ""

# Check Memory
echo "=== Memory Usage ==="
free -h | head -2

echo ""

# Check NAS Mount
echo "=== NAS Mount Status ==="
if mountpoint -q /mnt/mycosoft-nas; then
    echo "✅ NAS: Mounted at /mnt/mycosoft-nas"
    ls -la /mnt/mycosoft-nas/ | head -10
else
    echo "❌ NAS: Not mounted"
fi

echo ""
echo "=========================================="
echo "Health check completed"
echo "=========================================="
