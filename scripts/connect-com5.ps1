# Connect MycoBrain on COM5
# This script connects to the MycoBrain device on COM5 via the service API

$ErrorActionPreference = "Continue"

$ServiceUrl = "http://localhost:8003"
$Port = "COM5"

Write-Host "Connecting to MycoBrain on $Port..." -ForegroundColor Cyan

try {
    $result = Invoke-RestMethod -Uri "$ServiceUrl/devices/connect/$Port" `
        -Method POST `
        -ContentType "application/json" `
        -Body (@{port=$Port; baudrate=115200} | ConvertTo-Json) `
        -TimeoutSec 15
    
    Write-Host "Connection Result:" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 3
    
    if ($result.status -eq "connected") {
        Write-Host "`n✓ Successfully connected to $Port!" -ForegroundColor Green
        Write-Host "Device ID: $($result.device_id)" -ForegroundColor White
    } elseif ($result.status -eq "already_connected") {
        Write-Host "`n✓ Device already connected on $Port" -ForegroundColor Yellow
    } else {
        Write-Host "`n⚠ Connection status: $($result.status)" -ForegroundColor Yellow
    }
} catch {
    $errorMsg = $_.Exception.Message
    Write-Host "`n✗ Connection failed: $errorMsg" -ForegroundColor Red
    
    if ($errorMsg -like "*locked*" -or $errorMsg -like "*in use*" -or $errorMsg -like "*Access is denied*") {
        Write-Host "`nPort $Port is locked. Possible causes:" -ForegroundColor Yellow
        Write-Host "  - Another application is using the port (Arduino IDE, serial monitor, agent)" -ForegroundColor White
        Write-Host "  - Close the debugging agent or serial monitor" -ForegroundColor White
        Write-Host "  - Then try connecting again" -ForegroundColor White
    } elseif ($errorMsg -like "*timeout*") {
        Write-Host "`nConnection timed out. The device may not be responding." -ForegroundColor Yellow
        Write-Host "  - Check device is powered on" -ForegroundColor White
        Write-Host "  - Verify COM5 is the correct port" -ForegroundColor White
    }
}

Write-Host "`nChecking connected devices..." -ForegroundColor Cyan
try {
    $devices = Invoke-RestMethod -Uri "$ServiceUrl/devices" -TimeoutSec 5
    Write-Host "Connected devices: $($devices.count)" -ForegroundColor Green
    if ($devices.devices) {
        $devices.devices | ForEach-Object {
            Write-Host "  - $($_.device_id) on $($_.port) ($($_.status))" -ForegroundColor White
        }
    }
} catch {
    Write-Host "Could not fetch device list: $_" -ForegroundColor Yellow
}

























