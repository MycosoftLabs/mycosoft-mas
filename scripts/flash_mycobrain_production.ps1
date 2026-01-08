# Flash MycoBrain Production Firmware
# Flashes Side-A Production firmware to get device back online

param(
    [string]$Port = "COM6",
    [string]$FirmwarePath = "firmware\MycoBrain_SideA"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MycoBrain Production Firmware Flash" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Port: $Port"
Write-Host "Firmware: $FirmwarePath"
Write-Host ""

# Check if PlatformIO is available
$pioAvailable = $false
try {
    $pioVersion = pio --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] PlatformIO found: $pioVersion" -ForegroundColor Green
        $pioAvailable = $true
    }
} catch {
    Write-Host "[WARN] PlatformIO not found in PATH" -ForegroundColor Yellow
}

if (-not $pioAvailable) {
    Write-Host ""
    Write-Host "PlatformIO not available. Using Arduino IDE method:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Open Arduino IDE" -ForegroundColor White
    Write-Host "2. Open: $FirmwarePath\MycoBrain_SideA_Production.ino" -ForegroundColor White
    Write-Host "3. Select Board: ESP32S3 Dev Module" -ForegroundColor White
    Write-Host "4. Select Port: $Port" -ForegroundColor White
    Write-Host "5. Configure settings (see firmware\ARDUINO_IDE_SETTINGS.md)" -ForegroundColor White
    Write-Host "6. Click Upload" -ForegroundColor White
    Write-Host ""
    Write-Host "OR install PlatformIO and run:" -ForegroundColor Cyan
    Write-Host "  cd $FirmwarePath" -ForegroundColor White
    Write-Host "  pio run -t upload -e esp32-s3-devkitc-1 --upload-port $Port" -ForegroundColor White
    exit 1
}

# Use PlatformIO to flash
Write-Host ""
Write-Host "Flashing firmware with PlatformIO..." -ForegroundColor Cyan
Set-Location $FirmwarePath

try {
    Write-Host "Building firmware..." -ForegroundColor Yellow
    pio run 2>&1 | Out-Host
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Build failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "Uploading to $Port..." -ForegroundColor Yellow
    pio run -t upload --upload-port $Port 2>&1 | Out-Host
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Firmware uploaded successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Waiting for device to boot (5 seconds)..." -ForegroundColor Cyan
        Start-Sleep -Seconds 5
        
        Write-Host ""
        Write-Host "Testing device connection..." -ForegroundColor Cyan
        python ..\..\scripts\test_mycobrain_connection.py
        
    } else {
        Write-Host "[ERROR] Upload failed!" -ForegroundColor Red
        Write-Host "Check:" -ForegroundColor Yellow
        Write-Host "  - Device is in bootloader mode" -ForegroundColor White
        Write-Host "  - Port $Port is correct" -ForegroundColor White
        Write-Host "  - No other program is using the port" -ForegroundColor White
        exit 1
    }
    
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Set-Location ..\..
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Flash Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
