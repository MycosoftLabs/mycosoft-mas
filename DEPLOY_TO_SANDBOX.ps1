# ============================================================================
# Mycosoft Sandbox Deployment Script
# Run this manually to deploy to sandbox.mycosoft.com
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT SANDBOX DEPLOYMENT SCRIPT   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$VMHost = "192.168.0.187"
$VMUser = "mycosoft"
$VMPass = "REDACTED_VM_SSH_PASSWORD"

Write-Host "Target: $VMUser@$VMHost" -ForegroundColor Yellow
Write-Host ""

# Commands to run on VM
$deployCommands = @"
#!/bin/bash
set -e

echo "=========================================="
echo "  Starting Mycosoft Sandbox Deployment   "
echo "=========================================="

cd /opt/mycosoft/website

echo ""
echo "[1/7] Pulling latest code from GitHub..."
git pull origin main

echo ""
echo "[2/7] Checking MINDEX database (PostGIS)..."
docker exec -it mindex-postgres psql -U mindex -c "\dx" 2>/dev/null || echo "PostGIS check skipped - container may not be running"

echo ""
echo "[3/7] Enabling PostGIS if needed..."
docker exec -it mindex-postgres psql -U mindex -c "CREATE EXTENSION IF NOT EXISTS postgis;" 2>/dev/null || echo "PostGIS already enabled or container not running"

echo ""
echo "[4/7] Building website container (no cache)..."
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache

echo ""
echo "[5/7] Restarting website container..."
docker compose -f docker-compose.always-on.yml up -d mycosoft-website

echo ""
echo "[6/7] Restarting Cloudflare tunnel..."
sudo systemctl restart cloudflared

echo ""
echo "[7/7] Checking container status..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=========================================="
echo "  Deployment Complete!                   "
echo "=========================================="
echo ""
echo "Test URLs:"
echo "  - https://sandbox.mycosoft.com"
echo "  - https://sandbox.mycosoft.com/admin"
echo "  - https://sandbox.mycosoft.com/natureos"
echo "  - https://sandbox.mycosoft.com/natureos/devices"
echo ""
"@

Write-Host "========================================" -ForegroundColor Green
Write-Host "  MANUAL SSH INSTRUCTIONS              " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open a new terminal and run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ssh mycosoft@192.168.0.187" -ForegroundColor White
Write-Host ""
Write-Host "Password: REDACTED_VM_SSH_PASSWORD" -ForegroundColor White
Write-Host ""
Write-Host "Then run these commands:" -ForegroundColor Yellow
Write-Host ""
Write-Host @"
# Pull latest code
cd /opt/mycosoft/website
git pull origin main

# Check PostGIS
docker exec mindex-postgres psql -U mindex -c "\dx"

# Enable PostGIS if needed
docker exec mindex-postgres psql -U mindex -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Rebuild website
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache

# Restart website
docker compose -f docker-compose.always-on.yml up -d mycosoft-website

# Restart tunnel
sudo systemctl restart cloudflared

# Check status
docker ps
"@ -ForegroundColor Cyan

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  CLOUDFLARE CACHE CLEAR               " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "After deployment, clear Cloudflare cache:" -ForegroundColor Yellow
Write-Host "  1. Go to: https://dash.cloudflare.com" -ForegroundColor White
Write-Host "  2. Select mycosoft.com domain" -ForegroundColor White
Write-Host "  3. Caching > Configuration > Purge Everything" -ForegroundColor White
Write-Host ""

# Try to open Cloudflare dashboard
Write-Host "Opening Cloudflare dashboard..." -ForegroundColor Yellow
Start-Process "https://dash.cloudflare.com"

Write-Host ""
Write-Host "Script complete. Follow the manual steps above." -ForegroundColor Green
