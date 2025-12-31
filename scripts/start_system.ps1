# Start Complete System
$ErrorActionPreference = "Continue"

Write-Host "Starting Mycosoft System..." -ForegroundColor Cyan

# 1. Free ports
Write-Host "`n[1/5] Freeing ports..."
taskkill /F /IM python.exe 2>&1 | Out-Null
taskkill /F /IM node.exe 2>&1 | Out-Null
Start-Sleep -Seconds 3

# 2. Start MINDEX
Write-Host "[2/5] Starting MINDEX (8000)..."
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
Start-Process python -ArgumentList "services\mindex\api.py" -WindowStyle Hidden
Start-Sleep -Seconds 5

$health = Invoke-RestMethod http://localhost:8000/health -ErrorAction SilentlyContinue
if ($health) {
    Write-Host "  MINDEX: ONLINE v$($health.version)" -ForegroundColor Green
}

# 3. Start MycoBrain
Write-Host "[3/5] Starting MycoBrain (8003)..."
Start-Process python -ArgumentList "services\mycobrain\mycobrain_service_standalone.py" -WindowStyle Hidden
Start-Sleep -Seconds 5

$health = Invoke-RestMethod http://localhost:8003/health -ErrorAction SilentlyContinue
if ($health) {
    Write-Host "  MycoBrain: ONLINE v$($health.version)" -ForegroundColor Green
    $connect = Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM5" -Method POST -ErrorAction SilentlyContinue
    if ($connect) {
        Write-Host "  COM5: Connected" -ForegroundColor Green
    }
}

# 4. Start Website
Write-Host "[4/5] Starting Website (3000)..."
docker rm -f mycosoft-website 2>$null
docker run -d --name mycosoft-website -p 3000:3000 -e "MYCOBRAIN_SERVICE_URL=http://host.docker.internal:8003" -e "MINDEX_SERVICE_URL=http://host.docker.internal:8000" mycosoft-always-on-mycosoft-website:latest
Start-Sleep -Seconds 15

$web = Invoke-WebRequest http://localhost:3000 -TimeoutSec 10 -ErrorAction SilentlyContinue
if ($web) {
    Write-Host "  Website: ONLINE" -ForegroundColor Green
}

# 5. Summary
Write-Host "`n[5/5] System Status:"
Write-Host "  MINDEX (8000): $(if (Invoke-RestMethod http://localhost:8000/health -ErrorAction SilentlyContinue) {'ONLINE'} else {'OFFLINE'})" 
Write-Host "  MycoBrain (8003): $(if (Invoke-RestMethod http://localhost:8003/health -ErrorAction SilentlyContinue) {'ONLINE'} else {'OFFLINE'})"
Write-Host "  Website (3000): $(if (Invoke-WebRequest http://localhost:3000 -ErrorAction SilentlyContinue) {'ONLINE'} else {'OFFLINE'})"

Write-Host "`nAccess: http://localhost:3000/natureos/devices" -ForegroundColor Cyan

