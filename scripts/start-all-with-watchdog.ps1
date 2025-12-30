# Start all MYCOSOFT services and launch watchdog
# This script ensures everything starts and stays running

$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$WatchdogScript = "$MASDir\scripts\watchdog-services.ps1"

Write-Host "Starting MYCOSOFT services..." -ForegroundColor Cyan

# First, start all services
& "$MASDir\scripts\startup-all-services.ps1"

Write-Host ""
Write-Host "Starting watchdog service..." -ForegroundColor Cyan

# Check if watchdog is already running
$watchdogRunning = Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*watchdog-services*"
}

if ($watchdogRunning) {
    Write-Host "Watchdog is already running!" -ForegroundColor Yellow
} else {
    # Start watchdog in background
    Start-Process powershell.exe -ArgumentList "-NoProfile", "-ExecutionPolicy Bypass", "-File", "`"$WatchdogScript`"" -WindowStyle Hidden
    
    Write-Host "Watchdog started in background!" -ForegroundColor Green
}

Write-Host ""
Write-Host "All services and watchdog are running!" -ForegroundColor Green
Write-Host "Services will auto-restart if they crash." -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop watchdog, kill the PowerShell process running watchdog-services.ps1" -ForegroundColor Gray
