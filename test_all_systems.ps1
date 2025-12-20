# Comprehensive MAS System Test - All Components
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT MAS - COMPREHENSIVE SYSTEM TEST" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$global:TestResults = @()
$global:Passed = 0
$global:Failed = 0
$global:Warnings = 0

function Add-TestResult {
    param(
        [string]$Component,
        [string]$Test,
        [string]$Status,
        [string]$Details
    )
    
    $result = @{
        Component = $Component
        Test = $Test
        Status = $Status
        Details = $Details
        Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    
    $global:TestResults += $result
    
    switch ($Status) {
        "PASS" { $global:Passed++; $color = "Green" }
        "FAIL" { $global:Failed++; $color = "Red" }
        "WARN" { $global:Warnings++; $color = "Yellow" }
    }
    
    Write-Host "[$Status] $Component - $Test" -ForegroundColor $color
    if ($Details) {
        Write-Host "    $Details" -ForegroundColor Gray
    }
}

# =============================================================================
# INFRASTRUCTURE TESTS
# =============================================================================
Write-Host "`n--- INFRASTRUCTURE SERVICES ---" -ForegroundColor Yellow

# PostgreSQL
try {
    $pg = docker ps --filter "name=mas-postgres" --format "{{.Status}}"
    if ($pg -match "healthy") {
        Add-TestResult "Infrastructure" "PostgreSQL Container" "PASS" $pg
    } else {
        Add-TestResult "Infrastructure" "PostgreSQL Container" "WARN" $pg
    }
} catch {
    Add-TestResult "Infrastructure" "PostgreSQL Container" "FAIL" $_.Exception.Message
}

# Redis
try {
    $redis = docker ps --filter "name=redis" --format "{{.Status}}" | Select-Object -First 1
    if ($redis) {
        Add-TestResult "Infrastructure" "Redis Container" "PASS" $redis
    } else {
        Add-TestResult "Infrastructure" "Redis Container" "FAIL" "Not found"
    }
} catch {
    Add-TestResult "Infrastructure" "Redis Container" "FAIL" $_.Exception.Message
}

# Qdrant
try {
    $qdrant = docker ps --filter "name=qdrant" --format "{{.Status}}" | Select-Object -First 1
    if ($qdrant) {
        Add-TestResult "Infrastructure" "Qdrant Container" "PASS" $qdrant
    } else {
        Add-TestResult "Infrastructure" "Qdrant Container" "FAIL" "Not found"
    }
} catch {
    Add-TestResult "Infrastructure" "Qdrant Container" "FAIL" $_.Exception.Message
}

# =============================================================================
# MAS CORE TESTS
# =============================================================================
Write-Host "`n--- MAS CORE SERVICES ---" -ForegroundColor Yellow

# Find MAS Orchestrator container
$masOrchestratorNames = @("omc-mas-orchestrator-1", "fjt-mas-orchestrator-1", "mas-orchestrator")
$masOrchestratorFound = $false

foreach ($name in $masOrchestratorNames) {
    $masOrch = docker ps --filter "name=$name" --format "{{.Status}}"
    if ($masOrch) {
        Add-TestResult "MAS Core" "Orchestrator Container ($name)" "PASS" $masOrch
        $masOrchestratorFound = $true
        break
    }
}

if (-not $masOrchestratorFound) {
    Add-TestResult "MAS Core" "Orchestrator Container" "FAIL" "Not found"
}

# Test MAS Health API
try {
    $health = curl.exe -s http://localhost:8001/health | ConvertFrom-Json
    if ($health.status -eq "ok") {
        Add-TestResult "MAS Core" "Health API" "PASS" "Status: $($health.status)"
    } else {
        Add-TestResult "MAS Core" "Health API" "WARN" "Status: $($health.status)"
    }
} catch {
    Add-TestResult "MAS Core" "Health API" "FAIL" $_.Exception.Message
}

# Test Agent Registry
try {
    $agents = curl.exe -s http://localhost:8001/agents/registry/ | ConvertFrom-Json
    $agentCount = ($agents | Measure-Object).Count
    Add-TestResult "MAS Core" "Agent Registry" "PASS" "$agentCount agents registered"
} catch {
    Add-TestResult "MAS Core" "Agent Registry" "FAIL" $_.Exception.Message
}

# =============================================================================
# VOICE SYSTEM TESTS
# =============================================================================
Write-Host "`n--- VOICE SYSTEM ---" -ForegroundColor Yellow

# Find containers with various prefixes
$voiceContainers = @{
    "Whisper STT" = @("omc-whisper-1", "mycosoft-mas-whisper-1")
    "OpenedAI Speech" = @("omc-openedai-speech-1", "mycosoft-mas-openedai-speech-1")
    "Voice UI" = @("omc-voice-ui-1", "lak-voice-ui-1")
    "ElevenLabs Proxy" = @("omc-elevenlabs-proxy-1", "mycosoft-mas-elevenlabs-proxy-1")
}

foreach ($service in $voiceContainers.Keys) {
    $found = $false
    foreach ($name in $voiceContainers[$service]) {
        $container = docker ps --filter "name=$name" --format "{{.Status}}"
        if ($container) {
            Add-TestResult "Voice System" "$service Container" "PASS" $container
            $found = $true
            break
        }
    }
    if (-not $found) {
        Add-TestResult "Voice System" "$service Container" "WARN" "Not found or not running"
    }
}

# Test Voice API Endpoints
try {
    $voiceAgents = curl.exe -s http://localhost:8001/voice/agents | ConvertFrom-Json
    Add-TestResult "Voice System" "Voice Agents API" "PASS" "Accessible"
} catch {
    Add-TestResult "Voice System" "Voice Agents API" "FAIL" $_.Exception.Message
}

try {
    $voiceFeedback = curl.exe -s http://localhost:8001/voice/feedback/summary | ConvertFrom-Json
    Add-TestResult "Voice System" "Feedback System" "PASS" "Total: $($voiceFeedback.total), Avg: $([math]::Round($voiceFeedback.avg_rating,2))"
} catch {
    Add-TestResult "Voice System" "Feedback System" "FAIL" $_.Exception.Message
}

# =============================================================================
# DASHBOARD TESTS
# =============================================================================
Write-Host "`n--- DASHBOARDS & MONITORING ---" -ForegroundColor Yellow

# MYCA App
$mycaAppNames = @("omc-myca-app-1", "mycosoft-mas-myca-app-1")
$mycaFound = $false

foreach ($name in $mycaAppNames) {
    $myca = docker ps --filter "name=$name" --format "{{.Status}}"
    if ($myca) {
        Add-TestResult "Dashboard" "MYCA App Container" "PASS" $myca
        $mycaFound = $true
        
        # Test accessibility
        try {
            $response = curl.exe -s -o $null -w "%{http_code}" http://localhost:3001/
            if ($response -eq "200") {
                Add-TestResult "Dashboard" "MYCA Web Interface" "PASS" "HTTP $response"
            } else {
                Add-TestResult "Dashboard" "MYCA Web Interface" "WARN" "HTTP $response"
            }
        } catch {
            Add-TestResult "Dashboard" "MYCA Web Interface" "FAIL" $_.Exception.Message
        }
        break
    }
}

if (-not $mycaFound) {
    Add-TestResult "Dashboard" "MYCA App Container" "WARN" "Not found"
}

# Grafana
$grafana = docker ps --filter "name=grafana" --format "{{.Status}}" | Select-Object -First 1
if ($grafana) {
    Add-TestResult "Dashboard" "Grafana Container" "PASS" $grafana
    try {
        $grafanaHealth = curl.exe -s http://localhost:3000/api/health | ConvertFrom-Json
        Add-TestResult "Dashboard" "Grafana API" "PASS" "Database: $($grafanaHealth.database)"
    } catch {
        Add-TestResult "Dashboard" "Grafana API" "WARN" $_.Exception.Message
    }
} else {
    Add-TestResult "Dashboard" "Grafana Container" "WARN" "Not found"
}

# Prometheus
$prometheus = docker ps --filter "name=prometheus" --format "{{.Status}}" | Select-Object -First 1
if ($prometheus) {
    Add-TestResult "Dashboard" "Prometheus Container" "PASS" $prometheus
    try {
        $promResponse = curl.exe -s -o $null -w "%{http_code}" http://localhost:9090/-/healthy
        if ($promResponse -eq "200") {
            Add-TestResult "Dashboard" "Prometheus API" "PASS" "HTTP $promResponse"
        }
    } catch {
        Add-TestResult "Dashboard" "Prometheus API" "WARN" $_.Exception.Message
    }
} else {
    Add-TestResult "Dashboard" "Prometheus Container" "WARN" "Not found"
}

# =============================================================================
# WORKFLOW AUTOMATION TESTS
# =============================================================================
Write-Host "`n--- WORKFLOW AUTOMATION ---" -ForegroundColor Yellow

$n8nNames = @("omc-n8n-1", "mycosoft-mas-n8n-1")
$n8nFound = $false

foreach ($name in $n8nNames) {
    $n8n = docker ps --filter "name=$name" --format "{{.Status}}"
    if ($n8n) {
        Add-TestResult "Automation" "n8n Container" "PASS" $n8n
        $n8nFound = $true
        
        # Test accessibility
        try {
            $response = curl.exe -s -o $null -w "%{http_code}" http://localhost:5678/
            if ($response -eq "200") {
                Add-TestResult "Automation" "n8n Web Interface" "PASS" "HTTP $response"
            } else {
                Add-TestResult "Automation" "n8n Web Interface" "WARN" "HTTP $response"
            }
        } catch {
            Add-TestResult "Automation" "n8n Web Interface" "FAIL" $_.Exception.Message
        }
        break
    }
}

if (-not $n8nFound) {
    Add-TestResult "Automation" "n8n Container" "WARN" "Not found"
}

# =============================================================================
# DATABASE TESTS
# =============================================================================
Write-Host "`n--- DATABASE CONNECTIVITY ---" -ForegroundColor Yellow

# PostgreSQL Connection
try {
    $pgTest = docker exec mas-postgres pg_isready -U mas 2>&1
    if ($LASTEXITCODE -eq 0) {
        Add-TestResult "Database" "PostgreSQL Connection" "PASS" "Ready"
    } else {
        Add-TestResult "Database" "PostgreSQL Connection" "WARN" $pgTest
    }
} catch {
    Add-TestResult "Database" "PostgreSQL Connection" "FAIL" $_.Exception.Message
}

# Redis Connection
$redisNames = @("mycosoft-mas-redis-1", "awm-redis-1", "mas-redis")
$redisFound = $false

foreach ($name in $redisNames) {
    try {
        $redisTest = docker exec $name redis-cli ping 2>&1
        if ($redisTest -match "PONG") {
            Add-TestResult "Database" "Redis Connection ($name)" "PASS" "PONG"
            $redisFound = $true
            break
        }
    } catch {
        # Continue to next
    }
}

if (-not $redisFound) {
    Add-TestResult "Database" "Redis Connection" "WARN" "Could not connect"
}

# Qdrant Connection
try {
    $qdrantTest = curl.exe -s http://localhost:6333/collections | ConvertFrom-Json
    Add-TestResult "Database" "Qdrant Connection" "PASS" "Collections API accessible"
} catch {
    Add-TestResult "Database" "Qdrant Connection" "FAIL" $_.Exception.Message
}

# =============================================================================
# FINAL SUMMARY
# =============================================================================
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  TEST SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$total = $global:Passed + $global:Failed + $global:Warnings

Write-Host "`nTotal Tests: $total" -ForegroundColor White
Write-Host "Passed:  $global:Passed" -ForegroundColor Green
Write-Host "Failed:  $global:Failed" -ForegroundColor Red
Write-Host "Warnings: $global:Warnings" -ForegroundColor Yellow

if ($global:Failed -gt 0) {
    Write-Host "`nCritical Failures:" -ForegroundColor Red
    $global:TestResults | Where-Object {$_.Status -eq "FAIL"} | ForEach-Object {
        Write-Host "  - $($_.Component) :: $($_.Test): $($_.Details)" -ForegroundColor Red
    }
}

# Save detailed report
$reportFile = "comprehensive_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$report = @{
    Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Summary = @{
        Total = $total
        Passed = $global:Passed
        Failed = $global:Failed
        Warnings = $global:Warnings
    }
    Results = $global:TestResults
}

$report | ConvertTo-Json -Depth 10 | Out-File $reportFile
Write-Host "`nDetailed report saved to: $reportFile" -ForegroundColor Cyan

Write-Host "`n============================================================" -ForegroundColor Cyan

# Return appropriate exit code
if ($global:Failed -gt 0) {
    exit 1
} else {
    exit 0
}
