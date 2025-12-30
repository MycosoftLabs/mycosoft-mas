# MYCOSOFT Complete Persistent Startup (Docker-based)
# Starts all core services in Docker so they stay running independently of Cursor.

$ErrorActionPreference = "Continue"

$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$ScriptDir = "$MASDir\scripts"
$LogDir = "$MASDir\logs"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT Persistent Service Startup      " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Change to MAS directory
Set-Location $MASDir

# 1. Start Docker Desktop if not running
Write-Host "[1/4] Checking Docker..." -ForegroundColor Cyan
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 30
    Write-Host "  Docker Desktop started" -ForegroundColor Green
} else {
    Write-Host "  Docker is running" -ForegroundColor Green
}

# 2. Start Always-On Docker Stack (Website + MINDEX + MycoBrain)
Write-Host ""
Write-Host "[2/4] Starting Always-On Docker stack..." -ForegroundColor Cyan

# Best-effort: attach MycoBoard USB into WSL2 so containers can open /dev/ttyACM0
try {
    & "$ScriptDir\attach-mycoboard-usbipd.ps1" | Out-Null
} catch {
    # Ignore attach errors; stack can still start without hardware
}

# Stop anything currently occupying the public ports
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 2

# Bring up Always-On stack (includes its own network + restart policies)
# If hardware is attached, the override will expose /dev/ttyACM0 into MycoBrain container.
docker compose -f docker-compose.always-on.yml -f docker-compose.always-on.hardware.yml up -d --build

Write-Host ""
Write-Host "Waiting 20 seconds for containers to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

# Verify services
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
$services = @(
    @{Name="Website"; Port=3000},
    @{Name="MycoBrain"; Port=8003},
    @{Name="MINDEX API"; Port=8000},
    @{Name="MAS Orchestrator"; Port=8001},
    @{Name="n8n Workflows"; Port=5678}
)

foreach ($svc in $services) {
    $connection = Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  $($svc.Name): " -NoNewline
        Write-Host "RUNNING" -ForegroundColor Green
    } else {
        Write-Host "  $($svc.Name): " -NoNewline
        Write-Host "STARTING..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "Services are running in Docker (independent of Cursor)." -ForegroundColor Green
Write-Host "Docker restart policies keep them always-on." -ForegroundColor Green
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "  .\scripts\stop-all-services.ps1" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan


