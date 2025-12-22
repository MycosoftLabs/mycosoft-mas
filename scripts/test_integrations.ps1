# Automated Integration Test Script
# Tests MINDEX, NATUREOS, and WEBSITE services

param(
    [int]$TimeoutSec = 30,
    [switch]$SkipWebsite
)

$ErrorActionPreference = "Continue"

Write-Host "=== Integration Services Test ===" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

function Test-Service {
    param(
        [string]$Name,
        [string]$Url,
        [string]$HealthEndpoint = "/health",
        [int]$ExpectedStatus = 200
    )
    
    Write-Host "Testing $Name..." -ForegroundColor Yellow
    try {
        $healthUrl = if ($HealthEndpoint -like "http*") { $HealthEndpoint } else { "$Url$HealthEndpoint" }
        $response = Invoke-WebRequest -Uri $healthUrl -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host "  ✓ $Name is healthy (HTTP $($response.StatusCode))" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ✗ $Name returned unexpected status: $($response.StatusCode)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "  ✗ $Name is not reachable: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-Database {
    param(
        [string]$Name,
        [string]$ConnectionString,
        [int]$Port
    )
    
    Write-Host "Testing $Name database..." -ForegroundColor Yellow
    try {
        # Test if port is listening
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
        if ($connection) {
            Write-Host "  ✓ $Name database port $Port is accessible" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ✗ $Name database port $Port is not accessible" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "  ✗ $Name database test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Test MINDEX
Write-Host "=== MINDEX Tests ===" -ForegroundColor Cyan
$mindexApi = Test-Service -Name "MINDEX API" -Url "http://localhost:8000"
$mindexDb = Test-Database -Name "MINDEX" -Port 5432
if (-not ($mindexApi -and $mindexDb)) { $allPassed = $false }

# Test NATUREOS
Write-Host ""
Write-Host "=== NATUREOS Tests ===" -ForegroundColor Cyan
$natureosApi = Test-Service -Name "NATUREOS API" -Url "http://localhost:8002"
$natureosDb = Test-Database -Name "NATUREOS" -Port 5435
if (-not ($natureosApi -and $natureosDb)) { $allPassed = $false }

# Test Website
if (-not $SkipWebsite) {
    Write-Host ""
    Write-Host "=== Website Tests ===" -ForegroundColor Cyan
    $website = Test-Service -Name "Website" -Url "http://localhost:3001" -HealthEndpoint "/"
    if (-not $website) { $allPassed = $false }
}

# Summary
Write-Host ""
Write-Host "=== Test Summary ===" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "✓ All integration services are healthy!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service URLs:" -ForegroundColor Yellow
    Write-Host "  - MINDEX API: http://localhost:8000" -ForegroundColor White
    Write-Host "  - NATUREOS API: http://localhost:8002" -ForegroundColor White
    if (-not $SkipWebsite) {
        Write-Host "  - Website: http://localhost:3001" -ForegroundColor White
    }
    exit 0
} else {
    Write-Host "✗ Some services failed. Check Docker containers:" -ForegroundColor Red
    Write-Host "  docker-compose -f docker-compose.integrations.yml ps" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.integrations.yml logs" -ForegroundColor Yellow
    exit 1
}
