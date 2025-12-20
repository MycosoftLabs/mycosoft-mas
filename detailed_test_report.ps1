# Detailed MAS Test Report Generator
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  MAS DETAILED TEST REPORT" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

$report = @{
    Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Tests = @()
}

# Test Voice System Endpoints
Write-Host "`n--- Testing Voice System Endpoints ---" -ForegroundColor Yellow

$voiceEndpoints = @(
    @{Name="Voice Orchestrator Chat"; Url="http://localhost:8001/voice/orchestrator/chat"; Method="POST"; Body='{"message":"test"}'},
    @{Name="Voice Agents List"; Url="http://localhost:8001/voice/agents"; Method="GET"},
    @{Name="Voice Feedback Summary"; Url="http://localhost:8001/voice/feedback/summary"; Method="GET"},
    @{Name="Voice Feedback Recent"; Url="http://localhost:8001/voice/feedback/recent?limit=5"; Method="GET"}
)

foreach ($endpoint in $voiceEndpoints) {
    try {
        if ($endpoint.Method -eq "GET") {
            $response = Invoke-WebRequest -Uri $endpoint.Url -UseBasicParsing -TimeoutSec 5
        } else {
            $response = Invoke-WebRequest -Uri $endpoint.Url -Method POST -Body $endpoint.Body -ContentType "application/json" -UseBasicParsing -TimeoutSec 10
        }
        
        Write-Host "[OK] $($endpoint.Name): Status $($response.StatusCode)" -ForegroundColor Green
        $report.Tests += @{
            Name = $endpoint.Name
            Status = "PASS"
            Details = "HTTP $($response.StatusCode)"
        }
    }
    catch {
        Write-Host "[FAIL] $($endpoint.Name): $($_.Exception.Message)" -ForegroundColor Red
        $report.Tests += @{
            Name = $endpoint.Name
            Status = "FAIL"
            Details = $_.Exception.Message
        }
    }
}

# Test Agent Registry
Write-Host "`n--- Testing Agent Registry ---" -ForegroundColor Yellow

try {
    $agentRegistry = Invoke-WebRequest -Uri "http://localhost:8001/agents/registry/" -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
    $agentCount = ($agentRegistry | Measure-Object).Count
    Write-Host "[OK] Agent Registry: $agentCount agents registered" -ForegroundColor Green
    Write-Host "Agents found:" -ForegroundColor Cyan
    $agentRegistry | ForEach-Object {
        if ($_.name) {
            Write-Host "  - $($_.name)" -ForegroundColor White
        }
    }
    
    $report.Tests += @{
        Name = "Agent Registry"
        Status = "PASS"
        Details = "$agentCount agents registered"
    }
}
catch {
    Write-Host "[FAIL] Agent Registry: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{
        Name = "Agent Registry"
        Status = "FAIL"
        Details = $_.Exception.Message
    }
}

# Test Database Connections
Write-Host "`n--- Testing Database Connections ---" -ForegroundColor Yellow

# PostgreSQL
try {
    $pgTest = docker exec mas-postgres psql -U mas -d mas -c "SELECT version();" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] PostgreSQL: Connected successfully" -ForegroundColor Green
        $report.Tests += @{Name = "PostgreSQL Connection"; Status = "PASS"; Details = "Connected"}
    } else {
        Write-Host "[FAIL] PostgreSQL: Connection failed" -ForegroundColor Red
        $report.Tests += @{Name = "PostgreSQL Connection"; Status = "FAIL"; Details = "Failed"}
    }
}
catch {
    Write-Host "[FAIL] PostgreSQL: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{Name = "PostgreSQL Connection"; Status = "FAIL"; Details = $_.Exception.Message}
}

# Redis
try {
    $redisTest = docker exec mycosoft-mas-redis-1 redis-cli ping 2>&1
    if ($redisTest -match "PONG") {
        Write-Host "[OK] Redis: Connected successfully" -ForegroundColor Green
        $report.Tests += @{Name = "Redis Connection"; Status = "PASS"; Details = "PONG received"}
    } else {
        Write-Host "[FAIL] Redis: Connection failed" -ForegroundColor Red
        $report.Tests += @{Name = "Redis Connection"; Status = "FAIL"; Details = "No PONG"}
    }
}
catch {
    Write-Host "[FAIL] Redis: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{Name = "Redis Connection"; Status = "FAIL"; Details = $_.Exception.Message}
}

# Qdrant
try {
    $qdrantTest = Invoke-WebRequest -Uri "http://localhost:6333/collections" -UseBasicParsing
    $collections = $qdrantTest.Content | ConvertFrom-Json
    Write-Host "[OK] Qdrant: Connected, collections available" -ForegroundColor Green
    $report.Tests += @{Name = "Qdrant Connection"; Status = "PASS"; Details = "Connected"}
}
catch {
    Write-Host "[FAIL] Qdrant: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{Name = "Qdrant Connection"; Status = "FAIL"; Details = $_.Exception.Message}
}

# Test n8n Integration
Write-Host "`n--- Testing n8n Integration ---" -ForegroundColor Yellow

try {
    $n8nTest = Invoke-WebRequest -Uri "http://localhost:5678/" -UseBasicParsing -TimeoutSec 5
    Write-Host "[OK] n8n: Web interface accessible" -ForegroundColor Green
    $report.Tests += @{Name = "n8n Web Interface"; Status = "PASS"; Details = "Accessible"}
}
catch {
    Write-Host "[FAIL] n8n: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{Name = "n8n Web Interface"; Status = "FAIL"; Details = $_.Exception.Message}
}

# Test Dashboard Components
Write-Host "`n--- Testing Dashboard Components ---" -ForegroundColor Yellow

try {
    $grafanaTest = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing
    Write-Host "[OK] Grafana: Health endpoint responding" -ForegroundColor Green
    $report.Tests += @{Name = "Grafana Health"; Status = "PASS"; Details = "Responding"}
}
catch {
    Write-Host "[FAIL] Grafana: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{Name = "Grafana Health"; Status = "FAIL"; Details = $_.Exception.Message}
}

try {
    $promTest = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing
    Write-Host "[OK] Prometheus: Health endpoint responding" -ForegroundColor Green
    $report.Tests += @{Name = "Prometheus Health"; Status = "PASS"; Details = "Responding"}
}
catch {
    Write-Host "[FAIL] Prometheus: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{Name = "Prometheus Health"; Status = "FAIL"; Details = $_.Exception.Message}
}

try {
    $mycaTest = Invoke-WebRequest -Uri "http://localhost:3001/" -UseBasicParsing
    Write-Host "[OK] MYCA Web App: Accessible" -ForegroundColor Green
    $report.Tests += @{Name = "MYCA Web App"; Status = "PASS"; Details = "Accessible"}
}
catch {
    Write-Host "[FAIL] MYCA Web App: $($_.Exception.Message)" -ForegroundColor Red
    $report.Tests += @{Name = "MYCA Web App"; Status = "FAIL"; Details = $_.Exception.Message}
}

# Generate Summary
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  TEST SUMMARY" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

$passed = ($report.Tests | Where-Object {$_.Status -eq "PASS"} | Measure-Object).Count
$failed = ($report.Tests | Where-Object {$_.Status -eq "FAIL"} | Measure-Object).Count
$total = $report.Tests.Count

Write-Host "Total Tests: $total" -ForegroundColor White
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red

if ($failed -gt 0) {
    Write-Host "`nFailed Tests:" -ForegroundColor Red
    $report.Tests | Where-Object {$_.Status -eq "FAIL"} | ForEach-Object {
        Write-Host "  - $($_.Name): $($_.Details)" -ForegroundColor Yellow
    }
}

# Save to JSON
$reportFile = "detailed_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$report | ConvertTo-Json -Depth 10 | Out-File $reportFile
Write-Host "`nReport saved to: $reportFile" -ForegroundColor Cyan
