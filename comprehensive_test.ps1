# =============================================================================
# MYCOSOFT MAS - COMPREHENSIVE SYSTEM TEST
# =============================================================================
# This script performs end-to-end testing of the entire MYCOSOFT MAS platform
# including all agents, voice integration, dashboards, and external integrations
# =============================================================================

$ErrorActionPreference = "Continue"
$global:TestResults = @()
$global:PassedTests = 0
$global:FailedTests = 0
$global:WarningTests = 0

# Colors for output
$ColorPass = "Green"
$ColorFail = "Red"
$ColorWarn = "Yellow"
$ColorInfo = "Cyan"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

function Write-TestHeader {
    param([string]$Title)
    Write-Host "`n=================================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan
}

function Write-TestResult {
    param(
        [string]$TestName,
        [string]$Status,
        [string]$Message = ""
    )
    
    $result = @{
        Test = $TestName
        Status = $Status
        Message = $Message
        Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    
    $global:TestResults += $result
    
    switch ($Status) {
        "PASS" {
            Write-Host "[✓] $TestName" -ForegroundColor $ColorPass
            $global:PassedTests++
        }
        "FAIL" {
            Write-Host "[✗] $TestName" -ForegroundColor $ColorFail
            if ($Message) { Write-Host "    Error: $Message" -ForegroundColor $ColorFail }
            $global:FailedTests++
        }
        "WARN" {
            Write-Host "[!] $TestName" -ForegroundColor $ColorWarn
            if ($Message) { Write-Host "    Warning: $Message" -ForegroundColor $ColorWarn }
            $global:WarningTests++
        }
    }
}

function Test-HttpEndpoint {
    param(
        [string]$Url,
        [int]$ExpectedStatusCode = 200,
        [int]$TimeoutSeconds = 10
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -UseBasicParsing
        return @{
            Success = ($response.StatusCode -eq $ExpectedStatusCode)
            StatusCode = $response.StatusCode
            Content = $response.Content
        }
    }
    catch {
        return @{
            Success = $false
            StatusCode = 0
            Content = $_.Exception.Message
        }
    }
}

function Test-DockerContainer {
    param(
        [string]$ContainerName,
        [string]$ExpectedStatus = "running"
    )
    
    try {
        $container = docker ps -a --filter "name=$ContainerName" --format "{{.Status}}" | Select-Object -First 1
        if ($container) {
            $isHealthy = $container -match "healthy" -or $container -match "Up"
            return @{
                Exists = $true
                Running = $isHealthy
                Status = $container
            }
        }
        return @{ Exists = $false; Running = $false; Status = "Not Found" }
    }
    catch {
        return @{ Exists = $false; Running = $false; Status = "Error: $($_.Exception.Message)" }
    }
}

# =============================================================================
# TEST SECTION 1: INFRASTRUCTURE SERVICES
# =============================================================================

function Test-InfrastructureServices {
    Write-TestHeader "TESTING INFRASTRUCTURE SERVICES"
    
    # Test Docker
    Write-Host "`nChecking Docker..." -ForegroundColor $ColorInfo
    try {
        $dockerVersion = docker --version
        Write-TestResult "Docker Installation" "PASS" $dockerVersion
    }
    catch {
        Write-TestResult "Docker Installation" "FAIL" "Docker not found or not running"
        return
    }
    
    # Test PostgreSQL
    Write-Host "`nChecking PostgreSQL..." -ForegroundColor $ColorInfo
    $pgContainer = Test-DockerContainer "mas-postgres"
    if ($pgContainer.Running) {
        Write-TestResult "PostgreSQL Container" "PASS" $pgContainer.Status
        
        # Test PostgreSQL connection
        try {
            $pgTest = docker exec mas-postgres pg_isready -U mas 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-TestResult "PostgreSQL Connection" "PASS"
            } else {
                Write-TestResult "PostgreSQL Connection" "WARN" $pgTest
            }
        }
        catch {
            Write-TestResult "PostgreSQL Connection" "FAIL" $_.Exception.Message
        }
    }
    else {
        Write-TestResult "PostgreSQL Container" "FAIL" $pgContainer.Status
    }
    
    # Test Redis
    Write-Host "`nChecking Redis..." -ForegroundColor $ColorInfo
    $redisContainers = @("mycosoft-mas-redis-1", "mas-redis")
    $redisFound = $false
    foreach ($container in $redisContainers) {
        $redisContainer = Test-DockerContainer $container
        if ($redisContainer.Running) {
            Write-TestResult "Redis Container ($container)" "PASS" $redisContainer.Status
            $redisFound = $true
            
            # Test Redis connection
            try {
                $redisTest = docker exec $container redis-cli ping 2>&1
                if ($redisTest -match "PONG") {
                    Write-TestResult "Redis Connection" "PASS"
                } else {
                    Write-TestResult "Redis Connection" "WARN" $redisTest
                }
            }
            catch {
                Write-TestResult "Redis Connection" "FAIL" $_.Exception.Message
            }
            break
        }
    }
    if (-not $redisFound) {
        Write-TestResult "Redis Container" "FAIL" "No Redis container found"
    }
    
    # Test Qdrant
    Write-Host "`nChecking Qdrant..." -ForegroundColor $ColorInfo
    $qdrantContainers = @("mycosoft-mas-qdrant-1", "mas-qdrant")
    $qdrantFound = $false
    foreach ($container in $qdrantContainers) {
        $qdrantContainer = Test-DockerContainer $container
        if ($qdrantContainer.Running) {
            Write-TestResult "Qdrant Container ($container)" "PASS" $qdrantContainer.Status
            $qdrantFound = $true
            
            # Test Qdrant API
            $qdrantTest = Test-HttpEndpoint "http://localhost:6333/readyz"
            if ($qdrantTest.Success) {
                Write-TestResult "Qdrant API" "PASS"
            } else {
                Write-TestResult "Qdrant API" "WARN" "Status: $($qdrantTest.StatusCode)"
            }
            break
        }
    }
    if (-not $qdrantFound) {
        Write-TestResult "Qdrant Container" "FAIL" "No Qdrant container found"
    }
    
    # Test LiteLLM
    Write-Host "`nChecking LiteLLM..." -ForegroundColor $ColorInfo
    $litellmContainer = Test-DockerContainer "mas-litellm"
    if ($litellmContainer.Exists) {
        Write-TestResult "LiteLLM Container" "PASS" $litellmContainer.Status
        
        $litellmTest = Test-HttpEndpoint "http://localhost:4000/health"
        if ($litellmTest.Success) {
            Write-TestResult "LiteLLM API" "PASS"
        } else {
            Write-TestResult "LiteLLM API" "WARN" "Status: $($litellmTest.StatusCode)"
        }
    }
    else {
        Write-TestResult "LiteLLM Container" "WARN" "Not found (may be optional)"
    }
}

# =============================================================================
# TEST SECTION 2: MAS CORE SERVICES
# =============================================================================

function Test-MASCore {
    Write-TestHeader "TESTING MAS CORE SERVICES"
    
    # Test MAS Orchestrator
    Write-Host "`nChecking MAS Orchestrator..." -ForegroundColor $ColorInfo
    $orchestratorContainers = @("fjt-mas-orchestrator-1", "mas-orchestrator")
    $orchestratorFound = $false
    
    foreach ($container in $orchestratorContainers) {
        $orchContainer = Test-DockerContainer $container
        if ($orchContainer.Running) {
            Write-TestResult "MAS Orchestrator Container ($container)" "PASS" $orchContainer.Status
            $orchestratorFound = $true
            
            # Test health endpoint
            $healthTest = Test-HttpEndpoint "http://localhost:8001/health"
            if ($healthTest.Success) {
                Write-TestResult "MAS Orchestrator Health API" "PASS"
                
                # Parse health response
                try {
                    $healthData = $healthTest.Content | ConvertFrom-Json
                    Write-Host "    Status: $($healthData.status)" -ForegroundColor $ColorInfo
                }
                catch {
                    Write-Host "    (Could not parse health response)" -ForegroundColor $ColorWarn
                }
            } else {
                Write-TestResult "MAS Orchestrator Health API" "FAIL" "Status: $($healthTest.StatusCode)"
            }
            
            # Test metrics endpoint
            $metricsTest = Test-HttpEndpoint "http://localhost:8001/metrics"
            if ($metricsTest.Success) {
                Write-TestResult "MAS Orchestrator Metrics API" "PASS"
            } else {
                Write-TestResult "MAS Orchestrator Metrics API" "WARN" "Status: $($metricsTest.StatusCode)"
            }
            
            break
        }
    }
    
    if (-not $orchestratorFound) {
        Write-TestResult "MAS Orchestrator Container" "FAIL" "No orchestrator container found"
    }
    
    # Test Agent Manager
    Write-Host "`nChecking Agent Manager..." -ForegroundColor $ColorInfo
    $agentManagerContainer = Test-DockerContainer "fjt-mas-agent-manager-1"
    if ($agentManagerContainer.Exists) {
        if ($agentManagerContainer.Running) {
            Write-TestResult "Agent Manager Container" "PASS" $agentManagerContainer.Status
        } else {
            Write-TestResult "Agent Manager Container" "WARN" $agentManagerContainer.Status
        }
    } else {
        Write-TestResult "Agent Manager Container" "WARN" "Not found (may be integrated)"
    }
    
    # Test Task Manager
    Write-Host "`nChecking Task Manager..." -ForegroundColor $ColorInfo
    $taskManagerContainer = Test-DockerContainer "fjt-mas-task-manager-1"
    if ($taskManagerContainer.Exists) {
        if ($taskManagerContainer.Running) {
            Write-TestResult "Task Manager Container" "PASS" $taskManagerContainer.Status
        } else {
            Write-TestResult "Task Manager Container" "WARN" $taskManagerContainer.Status
        }
    } else {
        Write-TestResult "Task Manager Container" "WARN" "Not found (may be integrated)"
    }
    
    # Test Integration Manager
    Write-Host "`nChecking Integration Manager..." -ForegroundColor $ColorInfo
    $integrationManagerContainer = Test-DockerContainer "fjt-mas-integration-manager-1"
    if ($integrationManagerContainer.Exists) {
        if ($integrationManagerContainer.Running) {
            Write-TestResult "Integration Manager Container" "PASS" $integrationManagerContainer.Status
        } else {
            Write-TestResult "Integration Manager Container" "WARN" $integrationManagerContainer.Status
        }
    } else {
        Write-TestResult "Integration Manager Container" "WARN" "Not found (may be integrated)"
    }
}

# =============================================================================
# TEST SECTION 3: VOICE SYSTEM
# =============================================================================

function Test-VoiceSystem {
    Write-TestHeader "TESTING VOICE SYSTEM (MYCA)"
    
    # Test Whisper STT
    Write-Host "`nChecking Whisper STT..." -ForegroundColor $ColorInfo
    $whisperContainers = @("mycosoft-mas-whisper-1", "fjt-whisper-1")
    $whisperFound = $false
    
    foreach ($container in $whisperContainers) {
        $whisperContainer = Test-DockerContainer $container
        if ($whisperContainer.Exists) {
            Write-TestResult "Whisper Container ($container)" "PASS" $whisperContainer.Status
            $whisperFound = $true
            
            # Test Whisper API
            $whisperTest = Test-HttpEndpoint "http://localhost:8765/docs"
            if ($whisperTest.Success) {
                Write-TestResult "Whisper API" "PASS"
            } else {
                Write-TestResult "Whisper API" "WARN" "Status: $($whisperTest.StatusCode)"
            }
            break
        }
    }
    
    if (-not $whisperFound) {
        Write-TestResult "Whisper Container" "WARN" "Not found"
    }
    
    # Test OpenedAI Speech (TTS)
    Write-Host "`nChecking OpenedAI Speech (TTS)..." -ForegroundColor $ColorInfo
    $ttsContainers = @("mycosoft-mas-openedai-speech-1", "fjt-openedai-speech-1")
    $ttsFound = $false
    
    foreach ($container in $ttsContainers) {
        $ttsContainer = Test-DockerContainer $container
        if ($ttsContainer.Exists) {
            Write-TestResult "OpenedAI Speech Container ($container)" "PASS" $ttsContainer.Status
            $ttsFound = $true
            
            # Test TTS API
            $ttsTest = Test-HttpEndpoint "http://localhost:5500/v1/models"
            if ($ttsTest.Success) {
                Write-TestResult "OpenedAI Speech API" "PASS"
            } else {
                Write-TestResult "OpenedAI Speech API" "WARN" "Status: $($ttsTest.StatusCode)"
            }
            break
        }
    }
    
    if (-not $ttsFound) {
        Write-TestResult "OpenedAI Speech Container" "WARN" "Not found"
    }
    
    # Test ElevenLabs Proxy
    Write-Host "`nChecking ElevenLabs Proxy..." -ForegroundColor $ColorInfo
    $elevenLabsContainers = @("mycosoft-mas-elevenlabs-proxy-1", "fjt-elevenlabs-proxy-1")
    $elevenLabsFound = $false
    
    foreach ($container in $elevenLabsContainers) {
        $elevenLabsContainer = Test-DockerContainer $container
        if ($elevenLabsContainer.Exists) {
            Write-TestResult "ElevenLabs Proxy Container ($container)" "PASS" $elevenLabsContainer.Status
            $elevenLabsFound = $true
            
            # Test ElevenLabs API
            $elevenLabsTest = Test-HttpEndpoint "http://localhost:5501/v1/audio/speech" 404
            if ($elevenLabsTest.Success) {
                Write-TestResult "ElevenLabs Proxy API" "PASS"
            } else {
                Write-TestResult "ElevenLabs Proxy API" "WARN" "Status: $($elevenLabsTest.StatusCode)"
            }
            break
        }
    }
    
    if (-not $elevenLabsFound) {
        Write-TestResult "ElevenLabs Proxy" "WARN" "Not found (optional premium feature)"
    }
    
    # Test Ollama (Local LLM)
    Write-Host "`nChecking Ollama..." -ForegroundColor $ColorInfo
    $ollamaContainers = @("mycosoft-mas-ollama-1", "fjt-ollama-1")
    $ollamaFound = $false
    
    foreach ($container in $ollamaContainers) {
        $ollamaContainer = Test-DockerContainer $container
        if ($ollamaContainer.Exists) {
            Write-TestResult "Ollama Container ($container)" "PASS" $ollamaContainer.Status
            $ollamaFound = $true
            
            # Test Ollama API
            $ollamaTest = Test-HttpEndpoint "http://localhost:11434/api/tags"
            if ($ollamaTest.Success) {
                Write-TestResult "Ollama API" "PASS"
            } else {
                Write-TestResult "Ollama API" "WARN" "Status: $($ollamaTest.StatusCode)"
            }
            break
        }
    }
    
    if (-not $ollamaFound) {
        Write-TestResult "Ollama Container" "WARN" "Not found (optional)"
    }
    
    # Test Voice UI
    Write-Host "`nChecking Voice UI..." -ForegroundColor $ColorInfo
    $voiceUIContainers = @("lak-voice-ui-1", "fjt-voice-ui-1")
    $voiceUIFound = $false
    
    foreach ($container in $voiceUIContainers) {
        $voiceUIContainer = Test-DockerContainer $container
        if ($voiceUIContainer.Exists) {
            Write-TestResult "Voice UI Container ($container)" "PASS" $voiceUIContainer.Status
            $voiceUIFound = $true
            
            # Test Voice UI
            $voiceUITest = Test-HttpEndpoint "http://localhost:8090/"
            if ($voiceUITest.Success) {
                Write-TestResult "Voice UI Web Interface" "PASS"
            } else {
                # Try alternate port
                $voiceUITest = Test-HttpEndpoint "http://localhost:8091/"
                if ($voiceUITest.Success) {
                    Write-TestResult "Voice UI Web Interface (port 8091)" "PASS"
                } else {
                    Write-TestResult "Voice UI Web Interface" "WARN" "Status: $($voiceUITest.StatusCode)"
                }
            }
            break
        }
    }
    
    if (-not $voiceUIFound) {
        Write-TestResult "Voice UI Container" "FAIL" "Not found"
    }
}

# =============================================================================
# TEST SECTION 4: DASHBOARD & WEB UI
# =============================================================================

function Test-DashboardUI {
    Write-TestHeader "TESTING DASHBOARD AND WEB UI"
    
    # Test MYCA Next.js App
    Write-Host "`nChecking MYCA Web App..." -ForegroundColor $ColorInfo
    $mycaAppContainers = @("mycosoft-mas-myca-app-1", "fjt-myca-app-1")
    $mycaAppFound = $false
    
    foreach ($container in $mycaAppContainers) {
        $mycaAppContainer = Test-DockerContainer $container
        if ($mycaAppContainer.Exists) {
            Write-TestResult "MYCA Web App Container ($container)" "PASS" $mycaAppContainer.Status
            $mycaAppFound = $true
            
            # Test MYCA UI
            $mycaTest = Test-HttpEndpoint "http://localhost:3001/"
            if ($mycaTest.Success) {
                Write-TestResult "MYCA Web Interface (port 3001)" "PASS"
            } else {
                # Try alternate port
                $mycaTest = Test-HttpEndpoint "http://localhost:3011/"
                if ($mycaTest.Success) {
                    Write-TestResult "MYCA Web Interface (port 3011)" "PASS"
                } else {
                    Write-TestResult "MYCA Web Interface" "WARN" "Status: $($mycaTest.StatusCode)"
                }
            }
            break
        }
    }
    
    if (-not $mycaAppFound) {
        Write-TestResult "MYCA Web App Container" "WARN" "Not found"
    }
    
    # Test Grafana
    Write-Host "`nChecking Grafana..." -ForegroundColor $ColorInfo
    $grafanaContainer = Test-DockerContainer "mas-grafana"
    if ($grafanaContainer.Running) {
        Write-TestResult "Grafana Container" "PASS" $grafanaContainer.Status
        
        # Test Grafana API
        $grafanaTest = Test-HttpEndpoint "http://localhost:3000/api/health"
        if ($grafanaTest.Success) {
            Write-TestResult "Grafana API" "PASS"
        } else {
            Write-TestResult "Grafana API" "WARN" "Status: $($grafanaTest.StatusCode)"
        }
    } else {
        Write-TestResult "Grafana Container" "WARN" $grafanaContainer.Status
    }
    
    # Test Prometheus
    Write-Host "`nChecking Prometheus..." -ForegroundColor $ColorInfo
    $promContainer = Test-DockerContainer "mas-prometheus"
    if ($promContainer.Running) {
        Write-TestResult "Prometheus Container" "PASS" $promContainer.Status
        
        # Test Prometheus API
        $promTest = Test-HttpEndpoint "http://localhost:9090/-/healthy"
        if ($promTest.Success) {
            Write-TestResult "Prometheus API" "PASS"
        } else {
            Write-TestResult "Prometheus API" "WARN" "Status: $($promTest.StatusCode)"
        }
    } else {
        Write-TestResult "Prometheus Container" "WARN" $promContainer.Status
    }
}

# =============================================================================
# TEST SECTION 5: WORKFLOW AUTOMATION
# =============================================================================

function Test-WorkflowAutomation {
    Write-TestHeader "TESTING WORKFLOW AUTOMATION"
    
    # Test n8n
    Write-Host "`nChecking n8n..." -ForegroundColor $ColorInfo
    $n8nContainers = @("mycosoft-mas-n8n-1", "fjt-n8n-1")
    $n8nFound = $false
    
    foreach ($container in $n8nContainers) {
        $n8nContainer = Test-DockerContainer $container
        if ($n8nContainer.Exists) {
            Write-TestResult "n8n Container ($container)" "PASS" $n8nContainer.Status
            $n8nFound = $true
            
            # Test n8n UI
            $n8nTest = Test-HttpEndpoint "http://localhost:5678/"
            if ($n8nTest.Success) {
                Write-TestResult "n8n Web Interface (port 5678)" "PASS"
            } else {
                # Try alternate port
                $n8nTest = Test-HttpEndpoint "http://localhost:5688/"
                if ($n8nTest.Success) {
                    Write-TestResult "n8n Web Interface (port 5688)" "PASS"
                } else {
                    Write-TestResult "n8n Web Interface" "WARN" "Status: $($n8nTest.StatusCode)"
                }
            }
            break
        }
    }
    
    if (-not $n8nFound) {
        Write-TestResult "n8n Container" "WARN" "Not found (optional)"
    }
}

# =============================================================================
# TEST SECTION 6: PYTHON TESTS
# =============================================================================

function Test-PythonTests {
    Write-TestHeader "RUNNING PYTHON UNIT TESTS"
    
    Write-Host "`nChecking Python environment..." -ForegroundColor $ColorInfo
    
    # Check if virtual environment exists
    $venvPaths = @(".\venv\Scripts\activate.ps1", ".\venv311\Scripts\activate.ps1", ".\.venv\Scripts\activate.ps1")
    $venvFound = $false
    
    foreach ($venvPath in $venvPaths) {
        if (Test-Path $venvPath) {
            Write-TestResult "Python Virtual Environment" "PASS" $venvPath
            $venvFound = $true
            
            # Activate venv and run tests
            Write-Host "`nRunning pytest..." -ForegroundColor $ColorInfo
            try {
                & $venvPath
                $pytestResult = pytest tests/ -v --tb=short --maxfail=5 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult "Python Unit Tests" "PASS"
                } elseif ($LASTEXITCODE -eq 5) {
                    Write-TestResult "Python Unit Tests" "WARN" "No tests collected"
                } else {
                    Write-TestResult "Python Unit Tests" "FAIL" "Exit code: $LASTEXITCODE"
                }
                Write-Host $pytestResult
            }
            catch {
                Write-TestResult "Python Unit Tests" "FAIL" $_.Exception.Message
            }
            break
        }
    }
    
    if (-not $venvFound) {
        Write-TestResult "Python Virtual Environment" "WARN" "Virtual environment not found, skipping Python tests"
    }
}

# =============================================================================
# TEST SECTION 7: INTEGRATION TESTS
# =============================================================================

function Test-Integrations {
    Write-TestHeader "TESTING EXTERNAL INTEGRATIONS"
    
    Write-Host "`nNote: Integration tests require configured API keys" -ForegroundColor $ColorWarn
    Write-Host "Skipping external API tests for now..." -ForegroundColor $ColorWarn
    
    # Placeholder for integration tests
    Write-TestResult "MINDEX Integration" "WARN" "Manual verification required"
    Write-TestResult "NATUREOS Integration" "WARN" "Manual verification required"
    Write-TestResult "MYCOBRAIN Integration" "WARN" "Manual verification required"
    Write-TestResult "Website Integration" "WARN" "Manual verification required"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

function Main {
    Clear-Host
    Write-Host "=================================================================" -ForegroundColor Cyan
    Write-Host "  MYCOSOFT MAS - COMPREHENSIVE SYSTEM TEST" -ForegroundColor Cyan
    Write-Host "  Starting at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan
    
    # Run all test sections
    Test-InfrastructureServices
    Test-MASCore
    Test-VoiceSystem
    Test-DashboardUI
    Test-WorkflowAutomation
    Test-PythonTests
    Test-Integrations
    
    # Generate summary report
    Write-TestHeader "TEST SUMMARY"
    
    Write-Host "`nTotal Tests: $($global:PassedTests + $global:FailedTests + $global:WarningTests)" -ForegroundColor $ColorInfo
    Write-Host "Passed: $global:PassedTests" -ForegroundColor $ColorPass
    Write-Host "Failed: $global:FailedTests" -ForegroundColor $ColorFail
    Write-Host "Warnings: $global:WarningTests" -ForegroundColor $ColorWarn
    
    # Save results to file
    $reportFile = "test_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $global:TestResults | ConvertTo-Json -Depth 10 | Out-File $reportFile
    Write-Host "`nDetailed results saved to: $reportFile" -ForegroundColor $ColorInfo
    
    Write-Host "`n=================================================================" -ForegroundColor Cyan
    Write-Host "  Test execution completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan
    
    # Return exit code based on results
    if ($global:FailedTests -gt 0) {
        exit 1
    } else {
        exit 0
    }
}

# Run main function
Main
