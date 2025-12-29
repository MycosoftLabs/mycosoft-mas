# MycoBrain Service Startup Script
# Starts the MycoBrain dual ESP32 service for device communication

Write-Host "Starting MycoBrain Service..." -ForegroundColor Cyan

$servicePath = Join-Path $PSScriptRoot "..\services\mycobrain\mycobrain_dual_service.py"
$servicePath = Resolve-Path $servicePath -ErrorAction SilentlyContinue

if (-not $servicePath) {
    Write-Host "ERROR: MycoBrain service not found at: $servicePath" -ForegroundColor Red
    exit 1
}

# Check if Python is available
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import serial; import fastapi; import uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing required packages..." -ForegroundColor Yellow
        pip install pyserial fastapi uvicorn pydantic
    }
} catch {
    Write-Host "Installing required packages..." -ForegroundColor Yellow
    pip install pyserial fastapi uvicorn pydantic
}

# Set environment variables
$env:MYCOBRAIN_SERVICE_PORT = "8003"
$env:PYTHONPATH = Join-Path $PSScriptRoot ".."

Write-Host "Starting service on port 8003..." -ForegroundColor Green
Write-Host "Service will be available at: http://localhost:8003" -ForegroundColor Green
Write-Host "API docs at: http://localhost:8003/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the service" -ForegroundColor Yellow
Write-Host ""

# Start the service
python $servicePath

