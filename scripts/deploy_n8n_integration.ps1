# Deploy n8n Integration Changes
# Date: January 27, 2026
# Purpose: Deploy website changes and configure VMs for n8n on MAS VM

Write-Host "=============================================="
Write-Host "N8N INTEGRATION DEPLOYMENT"
Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "=============================================="
Write-Host ""

# Step 1: Commit and push website changes
Write-Host "[1/5] Committing website changes..."
Set-Location "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
git add -A
git commit -m "fix: Update n8n webhook paths to use /myca/command (working endpoint)"
git push origin main

# Step 2: Commit and push MAS changes
Write-Host ""
Write-Host "[2/5] Committing MAS changes..."
Set-Location "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
git add -A
git commit -m "feat: Add n8n integration scripts and configuration (Jan 27, 2026)"
git push origin main

# Step 3: Instructions for Sandbox VM
Write-Host ""
Write-Host "[3/5] Sandbox VM Update Required (192.168.0.187)"
Write-Host "  SSH: ssh mycosoft@192.168.0.187"
Write-Host "  Then run:"
Write-Host "    cd /home/mycosoft/mycosoft/website"
Write-Host "    git reset --hard origin/main"
Write-Host "    docker build -t website-website:latest --no-cache ."
Write-Host "    docker compose -p mycosoft-production up -d mycosoft-website"
Write-Host ""
Write-Host "  To stop n8n on Sandbox (if still running):"
Write-Host "    docker compose stop n8n"
Write-Host ""

# Step 4: Instructions for MAS VM  
Write-Host "[4/5] MAS VM Update Required (192.168.0.188)"
Write-Host "  SSH: ssh mycosoft@192.168.0.188"
Write-Host "  Then run:"
Write-Host "    cd /home/mycosoft/mycosoft/mas"
Write-Host "    git reset --hard origin/main"
Write-Host ""

# Step 5: Cloudflare Cache
Write-Host "[5/5] Cloudflare Cache"
Write-Host "  Go to: https://dash.cloudflare.com"
Write-Host "  Select: mycosoft.com"
Write-Host "  Click: Caching -> Purge Everything"
Write-Host ""

Write-Host "=============================================="
Write-Host "DEPLOYMENT COMPLETE"
Write-Host "=============================================="
Write-Host ""
Write-Host "Verify at:"
Write-Host "  - https://sandbox.mycosoft.com/api/health"
Write-Host "  - http://192.168.0.188:5678/healthz (n8n on MAS)"
