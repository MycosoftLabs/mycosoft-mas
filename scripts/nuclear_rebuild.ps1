# Nuclear Option: Complete Docker Reset and Rebuild
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

Write-Host "=== NUCLEAR REBUILD - COMPLETE RESET ===" -ForegroundColor Red
Write-Host ""

# Stop everything
Write-Host "[1/8] Stopping all website containers..."
docker stop $(docker ps -aq --filter "name=website") 2>$null
docker rm $(docker ps -aq --filter "name=website") 2>$null

# Delete ALL website images
Write-Host "[2/8] Removing ALL website images..."
docker rmi -f $(docker images --filter "reference=*website*" -q) 2>$null
docker rmi -f $(docker images --filter "reference=mycosoft-always-on*" -q) 2>$null

# Prune EVERYTHING
Write-Host "[3/8] Pruning ALL Docker data..."
docker system prune -af --volumes

# Clean local
Write-Host "[4/8] Cleaning local files..."
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force node_modules/.cache -ErrorAction SilentlyContinue  
Remove-Item buggy-page.js -ErrorAction SilentlyContinue

# Verify source is clean
Write-Host "[5/8] Verifying source code..."
$check = Get-Content "app\natureos\devices\page.tsx" -Raw
if ($check -match "MycoBrainDeviceManager") {
    Write-Host "  ✓ Correct page.tsx found" -ForegroundColor Green
} else {
    Write-Host "  ✗ Wrong page.tsx!" -ForegroundColor Red
    exit 1
}

# Build with NEW hash by touching files
Write-Host "[6/8] Forcing file changes to generate new hash..."
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
Add-Content -Path "app\natureos\devices\page.tsx" -Value "`n// Build: $timestamp"

# Now rebuild
Write-Host "[7/8] Building completely fresh (3-4 min)..."
docker-compose -f docker-compose.always-on.yml build --pull --no-cache mycosoft-website

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Build successful!" -ForegroundColor Green
    
    Write-Host "[8/8] Starting website..."
    docker-compose -f docker-compose.always-on.yml up -d --no-deps mycosoft-website
    
    Start-Sleep -Seconds 20
    
    Write-Host "`n=== VERIFICATION ===" -ForegroundColor Cyan
    docker ps --filter "name=website"
    
    Write-Host "`nWebsite should be at: http://localhost:3000" -ForegroundColor White
    Write-Host "Device Manager: http://localhost:3000/natureos/devices" -ForegroundColor White
} else {
    Write-Host "✗ Build failed!" -ForegroundColor Red
}

