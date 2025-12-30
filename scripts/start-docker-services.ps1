# =============================================================================
# MYCOSOFT Docker Services Startup Script
# =============================================================================
# Starts all services in Docker containers and MycoBrain on host
# Services run independently of Cursor and auto-restart
#
# Usage:
#   .\scripts\start-docker-services.ps1
#   .\scripts\start-docker-services.ps1 -Rebuild
#   .\scripts\start-docker-services.ps1 -Stop
# =============================================================================

param(
    [switch]$Rebuild,
    [switch]$Stop,
    [switch]$Status
)

$ErrorActionPreference = "Continue"
$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$LogDir = "$MASDir\logs"

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT Docker Services Manager         " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $MASDir

# Status check
if ($Status) {
    Write-Host "Docker Container Status:" -ForegroundColor Cyan
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    Write-Host ""
    Write-Host "Service Health:" -ForegroundColor Cyan
    $services = @(
        @{Name="Website"; Port=3000; Url="http://localhost:3000"},
        @{Name="MINDEX"; Port=8000; Url="http://localhost:8000/health"},
        @{Name="MycoBrain"; Port=8003; Url="http://localhost:8003/health"},
        @{Name="n8n"; Port=5678; Url="http://localhost:5678"}
    )
    
    foreach ($svc in $services) {
        try {
            $null = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            Write-Host "  $($svc.Name) (port $($svc.Port)): " -NoNewline
            Write-Host "RUNNING" -ForegroundColor Green
        } catch {
            Write-Host "  $($svc.Name) (port $($svc.Port)): " -NoNewline
            Write-Host "STOPPED" -ForegroundColor Red
        }
    }
    exit 0
}

# Stop services
if ($Stop) {
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    
    # Stop Docker containers
    docker-compose -f docker-compose.services.yml down
    
    # Stop MycoBrain host service
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -like "*mycobrain_service*"
        } catch { $false }
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "All services stopped." -ForegroundColor Green
    exit 0
}

# =============================================================================
# 1. Check Docker
# =============================================================================
Write-Host "[1/5] Checking Docker..." -ForegroundColor Cyan
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    Write-Host "  Waiting for Docker to start (30 seconds)..."
    Start-Sleep -Seconds 30
}
Write-Host "  Docker is running" -ForegroundColor Green

# =============================================================================
# 2. Create Docker network
# =============================================================================
Write-Host ""
Write-Host "[2/5] Creating Docker network..." -ForegroundColor Cyan
docker network create mycosoft-services 2>$null
Write-Host "  Network ready" -ForegroundColor Green

# =============================================================================
# 3. Build and start Docker containers
# =============================================================================
Write-Host ""
Write-Host "[3/5] Starting Docker containers..." -ForegroundColor Cyan

if ($Rebuild) {
    Write-Host "  Building images (this may take several minutes)..." -ForegroundColor Yellow
    docker-compose -f docker-compose.services.yml build --no-cache
}

docker-compose -f docker-compose.services.yml up -d

Write-Host "  Docker containers started" -ForegroundColor Green

# =============================================================================
# 4. Start MycoBrain on host (for serial port access)
# =============================================================================
Write-Host ""
Write-Host "[4/5] Starting MycoBrain service on host..." -ForegroundColor Cyan

# MycoBrain needs to run on the host for COM port access on Windows
$existingMycoBrain = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*mycobrain_service*"
    } catch { $false }
}

if ($existingMycoBrain) {
    Write-Host "  MycoBrain already running (PID: $($existingMycoBrain.Id -join ', '))" -ForegroundColor Green
} else {
    $mycobrainLog = "$LogDir\mycobrain-service.log"
    $psCommand = "Set-Location '$MASDir'; python -m services.mycobrain.mycobrain_service_standalone 2>&1 | Tee-Object -FilePath '$mycobrainLog'"
    Start-Process powershell.exe -ArgumentList "-NoProfile", "-Command", $psCommand -WindowStyle Hidden
    Write-Host "  MycoBrain service started (log: $mycobrainLog)" -ForegroundColor Green
}

# =============================================================================
# 5. Start Watchdog
# =============================================================================
Write-Host ""
Write-Host "[5/5] Starting service watchdog..." -ForegroundColor Cyan

$existingWatchdog = Get-Process -Name "powershell" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*service-watchdog*"
    } catch { $false }
}

if ($existingWatchdog) {
    Write-Host "  Watchdog already running" -ForegroundColor Green
} else {
    $watchdogLog = "$LogDir\watchdog.log"
    $watchdogCommand = "Set-Location '$MASDir'; .\scripts\service-watchdog.ps1 -StartNow -CheckInterval 30 2>&1 | Tee-Object -FilePath '$watchdogLog'"
    Start-Process powershell.exe -ArgumentList "-NoProfile", "-Command", $watchdogCommand -WindowStyle Hidden
    Write-Host "  Watchdog started" -ForegroundColor Green
}

# =============================================================================
# Wait for services to start
# =============================================================================
Write-Host ""
Write-Host "Waiting for services to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# =============================================================================
# Show status
# =============================================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Service Status:" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "label=com.mycosoft.service"

Write-Host ""
$services = @(
    @{Name="Website"; Port=3000},
    @{Name="MINDEX"; Port=8000},
    @{Name="MycoBrain"; Port=8003},
    @{Name="n8n"; Port=5678}
)

foreach ($svc in $services) {
    $connection = Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  $($svc.Name) (port $($svc.Port)): " -NoNewline
        Write-Host "RUNNING" -ForegroundColor Green
    } else {
        Write-Host "  $($svc.Name) (port $($svc.Port)): " -NoNewline
        Write-Host "STARTING..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "All services are running in Docker!" -ForegroundColor Green
Write-Host ""
Write-Host "Access points:" -ForegroundColor Cyan
Write-Host "  Website:   http://localhost:3000" -ForegroundColor White
Write-Host "  MINDEX:    http://localhost:8000" -ForegroundColor White
Write-Host "  MycoBrain: http://localhost:8003" -ForegroundColor White
Write-Host "  n8n:       http://localhost:5678" -ForegroundColor White
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  Status:  .\scripts\start-docker-services.ps1 -Status" -ForegroundColor White
Write-Host "  Stop:    .\scripts\start-docker-services.ps1 -Stop" -ForegroundColor White
Write-Host "  Rebuild: .\scripts\start-docker-services.ps1 -Rebuild" -ForegroundColor White
Write-Host "  Logs:    docker-compose -f docker-compose.services.yml logs -f" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
