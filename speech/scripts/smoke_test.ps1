# PowerShell smoke test for speech gateway

$GATEWAY_URL = if ($env:GATEWAY_URL) { $env:GATEWAY_URL } else { "http://localhost:8002" }
$TEST_AUDIO = if ($env:TEST_AUDIO) { $env:TEST_AUDIO } else { "test_audio.webm" }

Write-Host "🧪 MYCA Speech Gateway Smoke Test" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if gateway is running
Write-Host "1. Checking gateway health..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/health" -Method Get -ErrorAction Stop
    if ($healthResponse.status -eq "ok") {
        Write-Host "✅ Gateway is healthy" -ForegroundColor Green
        Write-Host "   Response: $($healthResponse | ConvertTo-Json -Compress)"
    } else {
        Write-Host "❌ Gateway health check failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Gateway not reachable: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check available voices
Write-Host "2. Checking available voices..." -ForegroundColor Yellow
try {
    $voicesResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/voices" -Method Get -ErrorAction Stop
    if ($voicesResponse.voices) {
        Write-Host "✅ Voices endpoint working" -ForegroundColor Green
        Write-Host "   Available voices: $($voicesResponse.voices.Count)"
    } else {
        Write-Host "❌ Voices endpoint failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Voices endpoint error: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test speech turn (if test audio exists)
if (Test-Path $TEST_AUDIO) {
    Write-Host "3. Testing speech turn with audio file..." -ForegroundColor Yellow
    try {
        $formData = @{
            audio = Get-Item $TEST_AUDIO
            provider = "openai"
            voice = "alloy"
            store_audio = "false"
            wake_word_enabled = "false"
        }
        
        $response = Invoke-RestMethod -Uri "$GATEWAY_URL/speech/turn" -Method Post -Form $formData -ErrorAction Stop
        
        if ($response.request_id) {
            Write-Host "✅ Speech turn successful" -ForegroundColor Green
            Write-Host "   Request ID: $($response.request_id)"
            
            if ($response.transcript) {
                Write-Host "✅ Transcript received: $($response.transcript)" -ForegroundColor Green
            } else {
                Write-Host "⚠️  No transcript in response" -ForegroundColor Yellow
            }
            
            if ($response.tts_audio_base64) {
                Write-Host "✅ TTS audio received" -ForegroundColor Green
            } else {
                Write-Host "⚠️  No TTS audio in response" -ForegroundColor Yellow
            }
        } else {
            Write-Host "❌ Speech turn failed" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "❌ Speech turn error: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "⚠️  Test audio file not found: $TEST_AUDIO" -ForegroundColor Yellow
    Write-Host "   Skipping speech turn test" -ForegroundColor Yellow
    Write-Host "   Create a test audio file or record one to test full pipeline" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "✅ Smoke test completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start the UI: cd speech/ui && npm install && npm run dev"
Write-Host "2. Open http://localhost:3000"
Write-Host "3. Test push-to-talk functionality"
