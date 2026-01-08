# Start All Services Properly
# No workarounds - proper production setup

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Complete Mycosoft System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Kill processes on port 3000 and 8000
Write-Host "[1/6] Freeing required ports..." -ForegroundColor Yellow
$portsToFree = @(3000, 8000, 8003)
foreach ($port in $portsToFree) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $procId = $conn.OwningProcess
        if ($procId -gt 0) {
            Write-Host "  Killing PID $procId on port $port"
            taskkill /F /PID $procId 2>&1 | Out-Null
        }
    }
}

Start-Sleep -Seconds 3
Write-Host "  ✓ Ports freed" -ForegroundColor Green

# 2. Start MINDEX locally (faster than Docker for testing)
Write-Host "[2/6] Starting MINDEX service..." -ForegroundColor Yellow
cd $ProjectRoot
Start-Process python -ArgumentList "services\mindex\api.py" -WindowStyle Hidden
Start-Sleep -Seconds 5

$health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
if ($health) {
    Write-Host "  ✓ MINDEX running: $($health.version)" -ForegroundColor Green
} else {
    Write-Host "  ✗ MINDEX failed to start" -ForegroundColor Red
}

# 3. Start MycoBrain service
Write-Host "[3/6] Starting MycoBrain service..." -ForegroundColor Yellow
Start-Process python -ArgumentList "services\mycobrain\mycobrain_service_standalone.py" -WindowStyle Hidden
Start-Sleep -Seconds 5

$health = Invoke-RestMethod -Uri "http://localhost:8003/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
if ($health) {
    Write-Host "  ✓ MycoBrain running: $($health.version)" -ForegroundColor Green
    
    # Auto-connect COM5
    Write-Host "  Connecting COM5..." -ForegroundColor Gray
    $connect = Invoke-RestMethod -Uri "http://localhost:8003/devices/connect/COM5" -Method POST -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($connect) {
        Write-Host "  ✓ COM5 connected: $($connect.device_id)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ COM5 not available or already connected" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ MycoBrain failed to start" -ForegroundColor Red
}

# 4. Start website container
Write-Host "[4/6] Starting website container..." -ForegroundColor Yellow

# Stop any existing website containers
docker stop mycosoft-always-on-mycosoft-website-1 2>$null
docker rm mycosoft-always-on-mycosoft-website-1 2>$null

# Start fresh website container
docker run -d --name mycosoft-always-on-mycosoft-website-1 -p 3000:3000 `
    -e "MYCOBRAIN_SERVICE_URL=http://host.docker.internal:8003" `
    -e "MINDEX_SERVICE_URL=http://host.docker.internal:8000" `
    -e "NEXT_PUBLIC_APP_URL=http://localhost:3000" `
    -e "NODE_ENV=production" `
    mycosoft-always-on-mycosoft-website:latest

Start-Sleep -Seconds 15

$websiteStatus = docker ps --filter "name=mycosoft-always-on-mycosoft-website-1" --format "{{.Status}}"
if ($websiteStatus) {
    Write-Host "  ✓ Website running: $websiteStatus" -ForegroundColor Green
} else {
    Write-Host "  ✗ Website failed to start" -ForegroundColor Red
}

# 5. Verify n8n and MAS
Write-Host "[5/6] Checking other services..." -ForegroundColor Yellow

$n8n = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -TimeoutSec 5 -ErrorAction SilentlyContinue
if ($n8n) {
    Write-Host "  ✓ n8n running" -ForegroundColor Green
} else {
    Write-Host "  ⚠ n8n not running" -ForegroundColor Yellow
}

$mas = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
if ($mas) {
    Write-Host "  ✓ MAS Orchestrator running" -ForegroundColor Green
} else {
    Write-Host "  ⚠ MAS Orchestrator not running" -ForegroundColor Yellow
}

# 6. Final status check
Write-Host "[6/6] System Status Summary" -ForegroundColor Yellow
Write-Host ""

$services = @(
    @{Name="MINDEX"; Port=8000; URL="http://localhost:8000/health"},
    @{Name="MycoBrain"; Port=8003; URL="http://localhost:8003/health"},
    @{Name="Website"; Port=3000; URL="http://localhost:3000"},
    @{Name="n8n"; Port=5678; URL="http://localhost:5678/healthz"},
    @{Name="MAS"; Port=8001; URL="http://localhost:8001/health"}
)

$allHealthy = $true
foreach ($service in $services) {
    if ($service.Name -eq "Website") {
        $test = Invoke-WebRequest -Uri $service.URL -TimeoutSec 5 -ErrorAction SilentlyContinue
    } else {
        $test = Invoke-RestMethod -Uri $service.URL -TimeoutSec 5 -ErrorAction SilentlyContinue
    }
    
    if ($test) {
        Write-Host "  ✓ $($service.Name) ($($service.Port)): ONLINE" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($service.Name) ($($service.Port)): OFFLINE" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""
if ($allHealthy) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "ALL SYSTEMS OPERATIONAL ✓" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access Points:" -ForegroundColor Cyan
    Write-Host "  Website: http://localhost:3000" -ForegroundColor White
    Write-Host "  Device Manager: http://localhost:3000/natureos/devices" -ForegroundColor White
    Write-Host "  MINDEX: http://localhost:3000/natureos/mindex" -ForegroundColor White
    Write-Host "  n8n: http://localhost:5678" -ForegroundColor White
} else {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "SOME SERVICES NEED ATTENTION" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
}

