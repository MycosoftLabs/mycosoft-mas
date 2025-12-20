# End-to-End Voice Integration Test
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  VOICE INTEGRATION E2E TEST" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Test 1: Voice Chat Endpoint
Write-Host "`n[TEST 1] Testing Voice Chat Endpoint..." -ForegroundColor Yellow
try {
    $chatBody = @{
        message = "Hello MYCA, what is the status of all agents?"
        want_audio = $false
    } | ConvertTo-Json

    $chatResponse = Invoke-WebRequest -Uri "http://localhost:8001/voice/orchestrator/chat" `
        -Method POST `
        -Body $chatBody `
        -ContentType "application/json" `
        -UseBasicParsing

    $chatData = $chatResponse.Content | ConvertFrom-Json
    Write-Host "[OK] Voice chat successful" -ForegroundColor Green
    Write-Host "Response: $($chatData.response_text)" -ForegroundColor White
    
} catch {
    Write-Host "[FAIL] Voice chat failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Voice Agents Status
Write-Host "`n[TEST 2] Checking Voice-Enabled Agents..." -ForegroundColor Yellow
try {
    $agentsResponse = Invoke-WebRequest -Uri "http://localhost:8001/voice/agents" -UseBasicParsing
    $agents = $agentsResponse.Content | ConvertFrom-Json
    
    if ($agents.agents.Count -gt 0) {
        Write-Host "[OK] Found $($agents.agents.Count) voice-enabled agents" -ForegroundColor Green
        $agents.agents | ForEach-Object {
            Write-Host "  - $($_.display_name) ($($_.agent_id))" -ForegroundColor Cyan
        }
    } else {
        Write-Host "[INFO] No voice-enabled agents currently active" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[FAIL] Failed to get voice agents: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Voice Feedback System
Write-Host "`n[TEST 3] Testing Voice Feedback System..." -ForegroundColor Yellow
try {
    $feedbackBody = @{
        conversation_id = "test-$(Get-Random)"
        agent_name = "Orchestrator"
        transcript = "test voice command"
        response_text = "test response"
        rating = 5
        success = $true
        notes = "Automated test feedback"
    } | ConvertTo-Json

    $feedbackResponse = Invoke-WebRequest -Uri "http://localhost:8001/voice/feedback" `
        -Method POST `
        -Body $feedbackBody `
        -ContentType "application/json" `
        -UseBasicParsing

    Write-Host "[OK] Feedback submitted successfully" -ForegroundColor Green
    
    # Get feedback summary
    $summaryResponse = Invoke-WebRequest -Uri "http://localhost:8001/voice/feedback/summary" -UseBasicParsing
    $summary = $summaryResponse.Content | ConvertFrom-Json
    Write-Host "[INFO] Feedback Summary:" -ForegroundColor Cyan
    Write-Host "  Total: $($summary.total)" -ForegroundColor White
    Write-Host "  Avg Rating: $([math]::Round($summary.avg_rating, 2))/5" -ForegroundColor White
    Write-Host "  Success Rate: $([math]::Round($summary.avg_success * 100, 1))%" -ForegroundColor White
    
} catch {
    Write-Host "[FAIL] Feedback system failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Whisper STT Status
Write-Host "`n[TEST 4] Checking Whisper STT Status..." -ForegroundColor Yellow
try {
    $whisperTest = Invoke-WebRequest -Uri "http://localhost:8765/docs" -UseBasicParsing
    Write-Host "[OK] Whisper STT is accessible" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Whisper STT not accessible: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 5: TTS Status
Write-Host "`n[TEST 5] Checking TTS Services..." -ForegroundColor Yellow
try {
    $ttsTest = Invoke-WebRequest -Uri "http://localhost:5500/v1/models" -UseBasicParsing
    Write-Host "[OK] OpenedAI Speech (TTS) is accessible" -ForegroundColor Green
} catch {
    Write-Host "[WARN] OpenedAI Speech not accessible: $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
    $elevenLabsTest = Invoke-WebRequest -Uri "http://localhost:5501/health" -UseBasicParsing -ErrorAction SilentlyContinue
    Write-Host "[OK] ElevenLabs Proxy is accessible" -ForegroundColor Green
} catch {
    Write-Host "[INFO] ElevenLabs Proxy not configured (optional)" -ForegroundColor Cyan
}

# Test 6: Voice UI Status
Write-Host "`n[TEST 6] Checking Voice UI..." -ForegroundColor Yellow
$voiceUIPorts = @(8090, 8091)
$voiceUIFound = $false

foreach ($port in $voiceUIPorts) {
    try {
        $voiceUITest = Invoke-WebRequest -Uri "http://localhost:$port/myca_voice_elevenlabs.html" -UseBasicParsing
        Write-Host "[OK] Voice UI accessible at port $port" -ForegroundColor Green
        $voiceUIFound = $true
        break
    } catch {
        # Continue to next port
    }
}

if (-not $voiceUIFound) {
    Write-Host "[WARN] Voice UI not accessible on standard ports" -ForegroundColor Yellow
}

# Test 7: Ollama LLM Status
Write-Host "`n[TEST 7] Checking Ollama LLM..." -ForegroundColor Yellow
try {
    $ollamaTest = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing
    $ollamaModels = $ollamaTest.Content | ConvertFrom-Json
    Write-Host "[OK] Ollama is accessible" -ForegroundColor Green
    if ($ollamaModels.models -and $ollamaModels.models.Count -gt 0) {
        Write-Host "[INFO] Available models:" -ForegroundColor Cyan
        $ollamaModels.models | ForEach-Object {
            Write-Host "  - $($_.name)" -ForegroundColor White
        }
    }
} catch {
    Write-Host "[WARN] Ollama not accessible (may be optional): $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  VOICE E2E TEST COMPLETE" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
