# Fixed startup script for MycoBrain service
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$websiteDir = Split-Path -Parent $scriptDir
$serviceScript = Join-Path $websiteDir "services\mycobrain\mycobrain_service.py"
$logFile = Join-Path $websiteDir "logs\mycobrain-service.log"
$errorLog = Join-Path $websiteDir "logs\mycobrain-service-errors.log"

# Create logs directory
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null

# Stop existing service
Write-Host "Checking for existing MycoBrain service..."
$existing = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmd -like "*mycobrain_service*"
    } catch {
        $false
    }
}

if ($existing) {
    Write-Host "Stopping existing service..."
    $existing | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Start new service with separate stdout/stderr
Write-Host "Starting MycoBrain service..."
Write-Host "  Service: $serviceScript"
Write-Host "  Log: $logFile"

Set-Location $websiteDir

# Use PowerShell to redirect properly
$job = Start-Job -ScriptBlock {
    param($script, $log, $errLog, $dir)
    Set-Location $dir
    python $script *> $log 2> $errLog
} -ArgumentList $serviceScript, $logFile, $errorLog, $websiteDir

Start-Sleep -Seconds 5

# Check if service is responding
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8003/health" -TimeoutSec 5
    Write-Host "[OK] MycoBrain service started successfully" -ForegroundColor Green
    Write-Host "  PID: $($job.Id)"
    Write-Host "  Log: $logFile"
} catch {
    Write-Host "[WARNING] Service may not have started. Check logs:" -ForegroundColor Yellow
    Write-Host "  $logFile"
    Write-Host "  $errorLog"
}
