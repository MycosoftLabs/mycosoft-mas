# Start MycoBrain Service
# Ensures service doesn't block COM ports needed for testing/flashing

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting MycoBrain Service" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if service is already running
$existingJob = Get-Job -Name "MycoBrainService" -ErrorAction SilentlyContinue
if ($existingJob) {
    Write-Host "`nService already running (Job ID: $($existingJob.Id))" -ForegroundColor Yellow
    Write-Host "Stopping existing service..." -ForegroundColor Yellow
    Stop-Job $existingJob
    Remove-Job $existingJob
    Start-Sleep -Seconds 1
}

# Change to project root
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# Start service in background job
Write-Host "`nStarting MycoBrain service..." -ForegroundColor Green
$job = Start-Job -ScriptBlock {
    Set-Location $using:projectRoot
    $env:MYCOBRAIN_SERVICE_PORT = "8003"
    $env:MYCOBRAIN_SERVICE_HOST = "0.0.0.0"
    # Don't set MYCOBRAIN_PORT - service connects on-demand via API
    python services/mycobrain/mycobrain_service.py
} -Name "MycoBrainService"

Start-Sleep -Seconds 3

# Check if service started
if ($job.State -eq "Running") {
    Write-Host "Service started successfully!" -ForegroundColor Green
    Write-Host "Job ID: $($job.Id)" -ForegroundColor Gray
    
    # Test health endpoint
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8003/health" -TimeoutSec 2 -UseBasicParsing
        $health = $response.Content | ConvertFrom-Json
        Write-Host "`nService Health Check:" -ForegroundColor Cyan
        Write-Host "  Status: $($health.status)" -ForegroundColor White
        Write-Host "  Version: $($health.version)" -ForegroundColor White
        Write-Host "  Devices Connected: $($health.devices_connected)" -ForegroundColor White
        Write-Host "`nService URL: http://localhost:8003" -ForegroundColor Green
    } catch {
        Write-Host "`nService started but health check failed (may still be initializing)" -ForegroundColor Yellow
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "IMPORTANT: Service does NOT auto-connect" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "`nThe service will NOT block COM ports." -ForegroundColor White
    Write-Host "It only connects when you call:" -ForegroundColor White
    Write-Host "  POST http://localhost:8003/devices/connect/{port}" -ForegroundColor Cyan
    Write-Host "`nYou can safely use COM ports for:" -ForegroundColor Green
    Write-Host "  - Arduino IDE uploads" -ForegroundColor White
    Write-Host "  - Serial monitoring" -ForegroundColor White
    Write-Host "  - Firmware flashing" -ForegroundColor White
    Write-Host "  - Testing scripts" -ForegroundColor White
    
} else {
    Write-Host "Service failed to start!" -ForegroundColor Red
    Write-Host "`nJob output:" -ForegroundColor Yellow
    Receive-Job $job
    Remove-Job $job
}

Write-Host "`nTo view service logs:" -ForegroundColor Gray
Write-Host "  Receive-Job -Name MycoBrainService" -ForegroundColor Cyan
Write-Host "`nTo stop service:" -ForegroundColor Gray
Write-Host "  Stop-Job -Name MycoBrainService; Remove-Job -Name MycoBrainService" -ForegroundColor Cyan
