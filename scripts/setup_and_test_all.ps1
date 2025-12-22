# Complete automated setup and test script
# Clones repos, starts Docker services, and tests everything

param(
    [switch]$SkipClone,
    [switch]$SkipTests,
    [switch]$SkipWebsite
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT MAS - Complete Setup & Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $PSScriptRoot

# Step 1: Setup integrations
Write-Host "Step 1: Setting up integration services..." -ForegroundColor Yellow
Write-Host ""
$setupScript = Join-Path $rootDir "scripts\setup_integrations_docker.ps1"
if (Test-Path $setupScript) {
    if ($SkipClone) {
        & $setupScript -SkipClone
    } else {
        & $setupScript
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "⚠ Setup completed with warnings. Continuing with tests..." -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ Setup script not found: $setupScript" -ForegroundColor Red
    exit 1
}

# Wait for services to be ready
Write-Host ""
Write-Host "Waiting for services to start (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Step 2: Test services
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "Step 2: Testing integration services..." -ForegroundColor Yellow
    Write-Host ""
    $testScript = Join-Path $rootDir "scripts\test_integrations.ps1"
    if (Test-Path $testScript) {
        if ($SkipWebsite) {
            & $testScript -SkipWebsite
        } else {
            & $testScript
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ All tests passed!" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "⚠ Some tests failed. Check service logs." -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠ Test script not found: $testScript" -ForegroundColor Yellow
    }
}

# Step 3: Update dashboard environment
Write-Host ""
Write-Host "Step 3: Dashboard integration configuration..." -ForegroundColor Yellow
$dashboardEnv = Join-Path $rootDir "unifi-dashboard\.env.local"
if (Test-Path $dashboardEnv) {
    Write-Host "  Dashboard .env.local exists" -ForegroundColor Green
    Write-Host "  Update these variables if needed:" -ForegroundColor Yellow
    Write-Host "    MINDEX_API_URL=http://localhost:8000" -ForegroundColor White
    Write-Host "    NATUREOS_API_URL=http://localhost:8002" -ForegroundColor White
    Write-Host "    WEBSITE_API_URL=http://localhost:3001/api" -ForegroundColor White
} else {
    Write-Host "  ⚠ Dashboard .env.local not found. Create it from .env.example" -ForegroundColor Yellow
}

# Step 4: Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Verify services are running:" -ForegroundColor White
Write-Host "     docker-compose -f docker-compose.integrations.yml ps" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. View service logs:" -ForegroundColor White
Write-Host "     docker-compose -f docker-compose.integrations.yml logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Test integration APIs:" -ForegroundColor White
Write-Host "     .\scripts\test_integrations.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Start dashboard:" -ForegroundColor White
Write-Host "     cd unifi-dashboard" -ForegroundColor Gray
Write-Host "     npm run dev" -ForegroundColor Gray
Write-Host ""
