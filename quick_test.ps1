# Quick MAS System Test
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT MAS - QUICK SYSTEM TEST" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

$passed = 0
$failed = 0
$warnings = 0

function Test-Service {
    param([string]$Name, [string]$Url)
    Write-Host "`nTesting $Name..." -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "[OK] $Name is responding (Status: $($response.StatusCode))" -ForegroundColor Green
        $script:passed++
        return $true
    }
    catch {
        Write-Host "[FAIL] $Name is not responding" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Yellow
        $script:failed++
        return $false
    }
}

function Test-Container {
    param([string]$Name)
    Write-Host "`nChecking container: $Name..." -ForegroundColor Cyan
    try {
        $status = docker ps --filter "name=$Name" --format "{{.Status}}" 2>$null
        if ($status) {
            Write-Host "[OK] Container $Name is running" -ForegroundColor Green
            $script:passed++
            return $true
        } else {
            Write-Host "[WARN] Container $Name not found or not running" -ForegroundColor Yellow
            $script:warnings++
            return $false
        }
    }
    catch {
        Write-Host "[FAIL] Error checking container $Name" -ForegroundColor Red
        $script:failed++
        return $false
    }
}

# Test Infrastructure
Write-Host "`n--- INFRASTRUCTURE SERVICES ---" -ForegroundColor Yellow
Test-Container "mas-postgres"
Test-Container "mycosoft-mas-redis-1"
Test-Container "mycosoft-mas-qdrant-1"

# Test MAS Core
Write-Host "`n--- MAS CORE SERVICES ---" -ForegroundColor Yellow
Test-Container "fjt-mas-orchestrator-1"
Test-Service "MAS Health API" "http://localhost:8001/health"
Test-Service "MAS Metrics API" "http://localhost:8001/metrics"

# Test Voice System
Write-Host "`n--- VOICE SYSTEM ---" -ForegroundColor Yellow
Test-Container "mycosoft-mas-whisper-1"
Test-Container "mycosoft-mas-openedai-speech-1"
Test-Container "lak-voice-ui-1"
Test-Service "Voice UI" "http://localhost:8090/"

# Test Dashboards
Write-Host "`n--- DASHBOARDS ---" -ForegroundColor Yellow
Test-Container "mycosoft-mas-myca-app-1"
Test-Container "mas-grafana"
Test-Container "mas-prometheus"
Test-Service "MYCA App" "http://localhost:3001/"
Test-Service "Grafana" "http://localhost:3000/api/health"
Test-Service "Prometheus" "http://localhost:9090/-/healthy"

# Test Workflow Automation
Write-Host "`n--- WORKFLOW AUTOMATION ---" -ForegroundColor Yellow
Test-Container "mycosoft-mas-n8n-1"
Test-Service "n8n" "http://localhost:5678/"

# Summary
Write-Host "`n===================================================================" -ForegroundColor Cyan
Write-Host "  TEST SUMMARY" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "Passed:   $passed" -ForegroundColor Green
Write-Host "Failed:   $failed" -ForegroundColor Red
Write-Host "Warnings: $warnings" -ForegroundColor Yellow
Write-Host "===================================================================" -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
} else {
    exit 0
}
