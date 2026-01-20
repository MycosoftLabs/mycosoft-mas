$ErrorActionPreference = "Stop"

Write-Host "Starting MycoBrain Minimal Service (FastAPI) on :8003..." -ForegroundColor Cyan

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Stop any process already bound to 8003
$portInUse = Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue
if ($portInUse) {
  Write-Host "Port 8003 is in use; stopping owning process..." -ForegroundColor Yellow
  Stop-Process -Id $portInUse.OwningProcess -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
}

$env:MYCOBRAIN_HOST = "0.0.0.0"
$env:MYCOBRAIN_PORT = "8003"
if (-not $env:BAUD_RATE) { $env:BAUD_RATE = "115200" }

# Log to repo logs/
$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$logFile = Join-Path $logsDir "mycobrain-minimal-service.log"
$errFile = Join-Path $logsDir "mycobrain-minimal-service.err.log"

Write-Host "Logging to: $logFile" -ForegroundColor DarkGray
Write-Host "Errors to:  $errFile" -ForegroundColor DarkGray

# Start uvicorn detached (so this script returns and can be used by Task Scheduler)
$args = "-m uvicorn minimal_mycobrain:app --host 0.0.0.0 --port 8003"
$proc = Start-Process python -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardOutput $logFile -RedirectStandardError $errFile

Start-Sleep -Seconds 2

try {
  $status = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://localhost:8003/health).StatusCode
  Write-Host "[OK] Service is responding: http://localhost:8003/health (HTTP $status)" -ForegroundColor Green
  Write-Host "PID: $($proc.Id)" -ForegroundColor Cyan
} catch {
  Write-Host "[WARN] Service may still be starting. Check logs: $logFile" -ForegroundColor Yellow
}

