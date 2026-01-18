# Mycosoft Sandbox Deployment Script
# Run this script to deploy the latest changes to sandbox.mycosoft.com
# 
# Usage: .\deploy-to-sandbox.ps1
#
# This script will SSH into VM 103 and run deployment commands
# You will be prompted for the password: Mushroom1!Mushroom1!

$vmHost = "192.168.0.187"
$vmUser = "mycosoft"
$password = "Mushroom1!Mushroom1!"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mycosoft Sandbox Deployment" -ForegroundColor Cyan
Write-Host "  Target: sandbox.mycosoft.com (VM 103)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Commands to run on the server
$deployCommands = @"
echo '=== Starting Deployment ==='
cd /opt/mycosoft/website

echo '=== Pulling latest code from GitHub ==='
git pull origin main

echo '=== Rebuilding website container ==='
docker-compose -f docker-compose.yml build mycosoft-website --no-cache

echo '=== Stopping old container ==='
docker-compose -f docker-compose.yml stop mycosoft-website

echo '=== Starting new container ==='
docker-compose -f docker-compose.yml up -d mycosoft-website

echo '=== Checking MINDEX database connection ==='
docker exec -it mindex-postgres psql -U mindex -c '\dx' 2>/dev/null || echo 'MINDEX Postgres not running locally'

echo '=== Restarting Cloudflare tunnel ==='
sudo systemctl restart cloudflared

echo '=== Waiting for services to start ==='
sleep 10

echo '=== Checking container status ==='
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo '=== Testing endpoints ==='
curl -s http://localhost:3000/api/health | head -c 200 || echo 'Website health check failed'
echo ''
curl -s http://localhost:8000/health | head -c 200 || echo 'MINDEX health check failed'

echo '=== Deployment Complete ==='
"@

Write-Host "Deployment Commands to Execute:" -ForegroundColor Yellow
Write-Host "--------------------------------" -ForegroundColor Yellow
Write-Host $deployCommands -ForegroundColor Gray
Write-Host ""
Write-Host "SSH Command:" -ForegroundColor Green
Write-Host "ssh $vmUser@$vmHost" -ForegroundColor White
Write-Host ""
Write-Host "Password: $password" -ForegroundColor Magenta
Write-Host ""
Write-Host "Press Enter to open SSH session, or Ctrl+C to cancel..." -ForegroundColor Cyan
Read-Host

# Start SSH session
Write-Host "Opening SSH session to $vmHost..." -ForegroundColor Green
Write-Host "After connecting, paste the deployment commands above." -ForegroundColor Yellow
Write-Host ""

ssh $vmUser@$vmHost
