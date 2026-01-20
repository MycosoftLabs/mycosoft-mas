# Start MycoBrain Service with Correct Settings
# Port 8003, Baud 115200, Machine Mode Enabled

Write-Host "Starting MycoBrain Service..." -ForegroundColor Cyan

# Navigate to service directory
$serviceDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\services\mycobrain"
if (-not (Test-Path $serviceDir)) {
    Write-Host "ERROR: Service directory not found: $serviceDir" -ForegroundColor Red
    exit 1
}

Set-Location $serviceDir

# Check if port 8003 is already in use
$portInUse = Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "WARNING: Port 8003 is already in use. Stopping existing process..." -ForegroundColor Yellow
    $process = Get-Process -Id $portInUse.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

# Start the service
Write-Host "Starting uvicorn on port 18003..." -ForegroundColor Green
$env:PORT = "18003"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$serviceDir'; python -m uvicorn mycobrain_service:app --host 0.0.0.0 --port 18003 --reload"

Start-Sleep -Seconds 3

# Verify service is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:18003/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "✅ MycoBrain service is running on port 18003" -ForegroundColor Green
    Write-Host "Service URL: http://localhost:18003" -ForegroundColor Cyan
} catch {
    Write-Host "⚠️  Service may still be starting. Check the service window." -ForegroundColor Yellow
}

Write-Host "`nAvailable COM ports:" -ForegroundColor Cyan
Get-WmiObject Win32_SerialPort | Where-Object {$_.DeviceID -like "COM*"} | Select-Object DeviceID, Description | Format-Table -AutoSize

Write-Host "`nTo connect boards:" -ForegroundColor Yellow
Write-Host "1. Open http://localhost:3000 in browser" -ForegroundColor White
Write-Host "2. Navigate to Device Manager" -ForegroundColor White
Write-Host "3. Connect Side-A (COM5) and Side-B (COM7)" -ForegroundColor White
Write-Host "4. Machine mode will be initialized automatically" -ForegroundColor White
