# Comprehensive Test and Improvement Script for MYCOSOFT MAS
# This script tests the entire system and improves it iteratively

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MYCOSOFT MAS Comprehensive Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
Set-Location $rootDir

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
$venvPath = Join-Path $rootDir "venv311"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv311
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

# Install/upgrade required packages for testing
Write-Host "Installing test dependencies..." -ForegroundColor Yellow
pip install -q aiohttp httpx pyyaml 2>&1 | Out-Null
Write-Host "  ✓ Test dependencies installed" -ForegroundColor Green

# Check if MAS is running
Write-Host "Checking if MAS is running..." -ForegroundColor Yellow
$masRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $masRunning = $true
        Write-Host "  ✓ MAS is running" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ MAS is not running. Will attempt to start it..." -ForegroundColor Yellow
}

# Start MAS if not running
if (-not $masRunning) {
    Write-Host "Starting MAS service..." -ForegroundColor Yellow
    
    # Check if config.yaml exists
    if (-not (Test-Path "config.yaml")) {
        Write-Host "  ✗ config.yaml not found. Creating default config..." -ForegroundColor Red
        Copy-Item "config.yaml.example" "config.yaml" -ErrorAction SilentlyContinue
    }
    
    # Start MAS in background
    Write-Host "  Starting MAS API server..." -ForegroundColor Yellow
    
    # Install uvicorn if not available
    pip install -q uvicorn fastapi 2>&1 | Out-Null
    
    $masProcess = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "mycosoft_mas.core.myca_main:app", "--host", "0.0.0.0", "--port", "8000" -PassThru -WindowStyle Hidden
    
    # Wait for MAS to start
    Write-Host "  Waiting for MAS to start..." -ForegroundColor Yellow
    $maxWait = 30
    $waited = 0
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 1
        $waited++
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "  ✓ MAS started successfully" -ForegroundColor Green
                $masRunning = $true
                break
            }
        } catch {
            # Still waiting
        }
    }
    
    if (-not $masRunning) {
        Write-Host "  ✗ MAS failed to start. Check logs for errors." -ForegroundColor Red
        Write-Host "  You may need to install dependencies: pip install -r requirements.txt" -ForegroundColor Yellow
        exit 1
    }
}

# Run comprehensive test suite
Write-Host ""
Write-Host "Running comprehensive test suite..." -ForegroundColor Cyan
Write-Host ""

try {
    python scripts\comprehensive_test_suite.py
    $testExitCode = $LASTEXITCODE
} catch {
    Write-Host "  ✗ Test suite failed to run: $_" -ForegroundColor Red
    $testExitCode = 1
}

# Generate test report
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($testExitCode -eq 0) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "✗ Some tests failed. Review output above." -ForegroundColor Red
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Review test failures above" -ForegroundColor White
    Write-Host "2. Check MAS logs for errors" -ForegroundColor White
    Write-Host "3. Ensure all dependencies are installed" -ForegroundColor White
    Write-Host "4. Verify configuration in config.yaml" -ForegroundColor White
}

Write-Host ""
Write-Host "MAS API is available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Health check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "Metrics: http://localhost:8000/metrics" -ForegroundColor Cyan
Write-Host "Voice agents: http://localhost:8000/voice/agents" -ForegroundColor Cyan

Write-Host ""
Write-Host "To stop MAS, press Ctrl+C or close this window." -ForegroundColor Yellow

# Keep script running if MAS was started by this script
if (-not $masRunning -and $masProcess) {
    Write-Host "Press Ctrl+C to stop MAS and exit..." -ForegroundColor Yellow
    try {
        Wait-Process -Id $masProcess.Id
    } catch {
        # Process already stopped
    }
}
