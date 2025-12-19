# Comprehensive MYCA MAS Integration Test Script
# Tests MAS API + Speech Services Integration

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "MYCA MAS Integration Test Suite" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$errors = 0
$tests = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Body = $null
    )
    
    $script:tests++
    Write-Host "[$($script:tests)] Testing $Name..." -NoNewline
    
    try {
        if ($Method -eq "POST" -and $Body) {
            $response = Invoke-WebRequest -Uri $Url -Method $Method -Body ($Body | ConvertTo-Json) -ContentType "application/json" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        } else {
            $response = Invoke-WebRequest -Uri $Url -Method $Method -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        }
        
        if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 201) {
            Write-Host " PASS" -ForegroundColor Green
            return $true
        } else {
            Write-Host " FAIL (Status: $($response.StatusCode))" -ForegroundColor Red
            $script:errors++
            return $false
        }
    } catch {
        Write-Host " FAIL ($($_.Exception.Message))" -ForegroundColor Red
        $script:errors++
        return $false
    }
}

function Test-JsonEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Body = $null
    )
    
    $script:tests++
    Write-Host "[$($script:tests)] Testing $Name..." -NoNewline
    
    try {
        if ($Method -eq "POST" -and $Body) {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Body ($Body | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
        } else {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -TimeoutSec 10 -ErrorAction Stop
        }
        
        Write-Host " PASS" -ForegroundColor Green
        return $response
    } catch {
        Write-Host " FAIL ($($_.Exception.Message))" -ForegroundColor Red
        $script:errors++
        return $null
    }
}

# Test 1: MAS Health
Write-Host "`n--- MAS Core Services ---" -ForegroundColor Yellow
Test-Endpoint "MAS Health" "http://localhost:8001/health"
$status = Test-JsonEndpoint "MAS Status" "http://localhost:8001/api/status"

# Test 2: Infrastructure API
Write-Host "`n--- Infrastructure API ---" -ForegroundColor Yellow
if ($status) {
    Write-Host "  Status retrieved successfully" -ForegroundColor Gray
}

# Test 3: Speech Services
Write-Host "`n--- Speech Services ---" -ForegroundColor Yellow
Test-Endpoint "Speech Gateway" "http://localhost:8002/health"
Test-Endpoint "n8n" "http://localhost:5678/"
Test-Endpoint "Voice UI" "http://localhost:8090/"

# Test 4: Docker Container Health
Write-Host "`n--- Docker Container Status ---" -ForegroundColor Yellow
$containerOutput = docker ps --format "{{.Names}}|{{.Status}}"
$healthy = 0
$unhealthy = 0
$total = 0

foreach ($line in $containerOutput) {
    if ($line) {
        $parts = $line -split '\|'
        if ($parts.Length -eq 2) {
            $total++
            $name = $parts[0]
            $status = $parts[1]
            if ($status -like "*healthy*" -or ($status -like "*Up*" -and $status -notlike "*unhealthy*")) {
                $healthy++
                Write-Host "  ${name}: ${status}" -ForegroundColor Green
            } else {
                $unhealthy++
                Write-Host "  ${name}: ${status}" -ForegroundColor Red
            }
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total Tests: $tests" -ForegroundColor White
Write-Host "Passed: $($tests - $errors)" -ForegroundColor Green
Write-Host "Failed: $errors" -ForegroundColor $(if ($errors -eq 0) { "Green" } else { "Red" })
Write-Host "Containers: $total total, $healthy healthy, $unhealthy unhealthy" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

if ($errors -eq 0 -and $unhealthy -eq 0) {
    Write-Host "ALL TESTS PASSED - MYCA MAS IS FULLY OPERATIONAL!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "SOME TESTS FAILED - CHECK LOGS ABOVE" -ForegroundColor Red
    exit 1
}
