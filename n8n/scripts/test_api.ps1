# MYCA n8n API Test Script
# Tests the MYCA Command API and Event Intake endpoints

param(
    [string]$N8nUrl = "http://localhost:5678",
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "MYCA n8n API Test Suite" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$testResults = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "POST",
        [hashtable]$Body = @{},
        [int]$ExpectedStatus = 200
    )
    
    Write-Host "Testing: $Name" -ForegroundColor Yellow
    if ($Verbose) {
        Write-Host "  URL: $Url" -ForegroundColor Gray
        Write-Host "  Method: $Method" -ForegroundColor Gray
        Write-Host "  Body: $(ConvertTo-Json $Body -Compress)" -ForegroundColor Gray
    }
    
    try {
        $headers = @{
            "Content-Type" = "application/json"
        }
        
        $params = @{
            Uri = $Url
            Method = $Method
            Headers = $headers
            UseBasicParsing = $true
            TimeoutSec = 10
        }
        
        if ($Body.Count -gt 0) {
            $params.Body = ConvertTo-Json $Body -Depth 10
        }
        
        $response = Invoke-WebRequest @params
        
        $success = $response.StatusCode -eq $ExpectedStatus
        $statusColor = if ($success) { "Green" } else { "Red" }
        $statusSymbol = if ($success) { "✓" } else { "✗" }
        
        Write-Host "  $statusSymbol Status: $($response.StatusCode)" -ForegroundColor $statusColor
        
        if ($Verbose -and $response.Content) {
            $responseObj = $response.Content | ConvertFrom-Json
            Write-Host "  Response: $(ConvertTo-Json $responseObj -Depth 2)" -ForegroundColor Gray
        }
        
        $script:testResults += @{
            Name = $Name
            Success = $success
            Status = $response.StatusCode
            Response = $response.Content
        }
        
        Write-Host ""
        return $success
        
    } catch {
        Write-Host "  ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        
        $script:testResults += @{
            Name = $Name
            Success = $false
            Status = 0
            Error = $_.Exception.Message
        }
        
        return $false
    }
}

# Test 1: Health Check
Write-Host "[Test 1/5] Health Check" -ForegroundColor Cyan
Test-Endpoint -Name "n8n Health" -Url "$N8nUrl/healthz" -Method "GET"

# Test 2: Command API - Read Action (Generic Connector)
Write-Host "[Test 2/5] Command API - Generic Read" -ForegroundColor Cyan
$commandBody = @{
    request_id = "test-$(Get-Random)"
    actor = "test-user"
    integration = "httpbin"
    action = "read"
    params = @{
        endpoint = "/get"
        method = "GET"
    }
    confirm = $false
}
Test-Endpoint -Name "Command API (HTTPBin)" -Url "$N8nUrl/webhook/myca/command" -Body $commandBody -ExpectedStatus 200

# Test 3: Command API - With Confirmation Required
Write-Host "[Test 3/5] Command API - Confirmation Gate" -ForegroundColor Cyan
$confirmBody = @{
    request_id = "test-$(Get-Random)"
    actor = "test-user"
    integration = "github"
    action = "create"
    params = @{
        endpoint = "/repos/test/test/issues"
        body = @{
            title = "Test Issue"
        }
    }
    confirm = $false
}
Test-Endpoint -Name "Command API (Confirmation Required)" -Url "$N8nUrl/webhook/myca/command" -Body $confirmBody -ExpectedStatus 403

# Test 4: Event Intake - Info Event
Write-Host "[Test 4/5] Event Intake - Info Severity" -ForegroundColor Cyan
$eventBody = @{
    source = "test-script"
    event_type = "test_event"
    severity = "info"
    data = @{
        message = "Test event from PowerShell"
        timestamp = (Get-Date).ToString("o")
    }
    correlation_id = "test-$(Get-Random)"
}
Test-Endpoint -Name "Event Intake (Info)" -Url "$N8nUrl/webhook/myca/event" -Body $eventBody -ExpectedStatus 202

# Test 5: Event Intake - Critical Event (should trigger alert)
Write-Host "[Test 5/5] Event Intake - Critical Severity" -ForegroundColor Cyan
$criticalEventBody = @{
    source = "test-script"
    event_type = "critical_test"
    severity = "critical"
    data = @{
        message = "Critical test event - should trigger alert"
        timestamp = (Get-Date).ToString("o")
    }
    correlation_id = "test-$(Get-Random)"
}
Test-Endpoint -Name "Event Intake (Critical)" -Url "$N8nUrl/webhook/myca/event" -Body $criticalEventBody -ExpectedStatus 202

# Summary
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
$successCount = ($testResults | Where-Object { $_.Success }).Count
$totalCount = $testResults.Count
$passRate = [math]::Round(($successCount / $totalCount) * 100, 1)

Write-Host "Passed: $successCount/$totalCount ($passRate%)" -ForegroundColor $(if ($successCount -eq $totalCount) { "Green" } else { "Yellow" })
Write-Host ""

if ($successCount -eq $totalCount) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "! Some tests failed. Check n8n logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs n8n" -ForegroundColor Gray
    exit 1
}
