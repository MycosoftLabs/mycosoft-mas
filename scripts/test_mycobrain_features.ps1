# MycoBrain Comprehensive Feature Test Suite
# Tests all NDJSON Machine Mode features systematically

param(
    [string]$DeviceId = "mycobrain-COM5",
    [string]$ServiceUrl = "http://localhost:8003"
)

$testResults = @()

function Test-Feature {
    param($Name, $Command, $ExpectedResponse = $null)
    
    Write-Host "`n[TEST] $Name" -ForegroundColor Cyan
    Write-Host "Command: $Command" -ForegroundColor Gray
    
    try {
        $body = @{ command = @{ cmd = $Command } } | ConvertTo-Json
        $result = Invoke-RestMethod -Uri "$ServiceUrl/devices/$DeviceId/command" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
        
        if ($result.status -eq "ok") {
            Write-Host "✅ SUCCESS: $($result.response)" -ForegroundColor Green
            $script:testResults += @{Name=$Name; Status="PASS"; Response=$result.response}
            return $true
        } else {
            Write-Host "⚠️  WARNING: $($result.status)" -ForegroundColor Yellow
            $script:testResults += @{Name=$Name; Status="WARN"; Response=$result.status}
            return $false
        }
    } catch {
        Write-Host "❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $script:testResults += @{Name=$Name; Status="FAIL"; Response=$_.Exception.Message}
        return $false
    }
    
    Start-Sleep -Milliseconds 500
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MYCOBRAIN COMPREHENSIVE FEATURE TESTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Device: $DeviceId"
Write-Host "Service: $ServiceUrl"
Write-Host ""

# ==========================================
# CATEGORY 1: LED COLOR PATTERNS
# ==========================================
Write-Host "`n=== CATEGORY 1: LED PATTERNS ===" -ForegroundColor Yellow

Test-Feature "LED Pattern: Solid" "led pattern solid"
Test-Feature "LED Pattern: Blink" "led pattern blink"
Test-Feature "LED Pattern: Breathe" "led pattern breathe"
Test-Feature "LED Pattern: Rainbow" "led pattern rainbow"
Test-Feature "LED Pattern: Chase" "led pattern chase"
Test-Feature "LED Pattern: Sparkle" "led pattern sparkle"

# ==========================================
# CATEGORY 2: BUZZER PRESET SOUNDS
# ==========================================
Write-Host "`n=== CATEGORY 2: BUZZER PRESETS ===" -ForegroundColor Yellow

Test-Feature "Buzzer: Coin" "coin"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: Bump" "bump"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: Power" "power"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: One-Up" "oneup"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: Morg.io" "morgio"
Start-Sleep -Seconds 1

# ==========================================
# CATEGORY 3: CUSTOM BUZZER TONES
# ==========================================
Write-Host "`n=== CATEGORY 3: CUSTOM TONES ===" -ForegroundColor Yellow

Test-Feature "Buzzer: 200Hz Low" "buzzer freq 200 duration 500"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: 1000Hz Mid" "buzzer freq 1000 duration 500"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: 5000Hz High" "buzzer freq 5000 duration 500"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: Short 100ms" "buzzer freq 1000 duration 100"
Start-Sleep -Seconds 1

Test-Feature "Buzzer: Long 2000ms" "buzzer freq 1000 duration 2000"
Start-Sleep -Seconds 2

# ==========================================
# CATEGORY 4: MUSICAL NOTES
# ==========================================
Write-Host "`n=== CATEGORY 4: MUSICAL NOTES ===" -ForegroundColor Yellow

Test-Feature "Note: C4 (261Hz)" "buzzer note c4"
Start-Sleep -Milliseconds 500

Test-Feature "Note: E4 (330Hz)" "buzzer note e4"
Start-Sleep -Milliseconds 500

Test-Feature "Note: G4 (392Hz)" "buzzer note g4"
Start-Sleep -Milliseconds 500

Test-Feature "Note: C5 (523Hz)" "buzzer note c5"
Start-Sleep -Milliseconds 500

# ==========================================
# CATEGORY 5: MACHINE MODE INITIALIZATION
# ==========================================
Write-Host "`n=== CATEGORY 5: NDJSON MACHINE MODE ===" -ForegroundColor Yellow

Test-Feature "Machine Mode: Initialize" "machine init"
Start-Sleep -Seconds 2

Test-Feature "Machine Mode: Status" "machine status"

# ==========================================
# CATEGORY 6: OPTICAL TX (Light Communication)
# ==========================================
Write-Host "`n=== CATEGORY 6: OPTICAL TX ===" -ForegroundColor Yellow

Test-Feature "Optical TX: Camera OOK" "optical tx profile camera_ook payload HELLO rate_hz 10 repeat 3"
Start-Sleep -Seconds 5

Test-Feature "Optical TX: Manchester" "optical tx profile camera_manchester payload TEST123 rate_hz 10 repeat 3"
Start-Sleep -Seconds 5

Test-Feature "Optical TX: Spatial Mod" "optical tx profile spatial_sm payload SPATIAL rate_hz 5 repeat 3"
Start-Sleep -Seconds 5

# ==========================================
# CATEGORY 7: ACOUSTIC TX (Sound Communication)
# ==========================================
Write-Host "`n=== CATEGORY 7: ACOUSTIC TX ===" -ForegroundColor Yellow

Test-Feature "Acoustic TX: Basic" "acoustic tx payload SOUND_DATA rate_hz 10 repeat 3"
Start-Sleep -Seconds 5

Test-Feature "Acoustic TX: Slow Rate" "acoustic tx payload SLOW rate_hz 5 repeat 2"
Start-Sleep -Seconds 5

Test-Feature "Acoustic TX: Fast Rate" "acoustic tx payload FAST rate_hz 20 repeat 2"
Start-Sleep -Seconds 5

# ==========================================
# CATEGORY 8: COMMUNICATIONS
# ==========================================
Write-Host "`n=== CATEGORY 8: COMMUNICATIONS ===" -ForegroundColor Yellow

Test-Feature "LoRa: Status" "lora status"
Test-Feature "LoRa: Initialize" "lora init"
Test-Feature "LoRa: Send Packet" "lora send HELLO_LORA"

Test-Feature "WiFi: Scan" "wifi scan"
Test-Feature "WiFi: Status" "wifi status"

Test-Feature "BLE: Status" "ble status"
Test-Feature "BLE: Start" "ble start"

Test-Feature "Mesh: Status" "mesh status"

# ==========================================
# SUMMARY
# ==========================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$passed = ($testResults | Where-Object {$_.Status -eq "PASS"}).Count
$warned = ($testResults | Where-Object {$_.Status -eq "WARN"}).Count
$failed = ($testResults | Where-Object {$_.Status -eq "FAIL"}).Count
$total = $testResults.Count

Write-Host "`nTotal Tests: $total"
Write-Host "✅ Passed: $passed" -ForegroundColor Green
Write-Host "⚠️  Warnings: $warned" -ForegroundColor Yellow
Write-Host "❌ Failed: $failed" -ForegroundColor Red

Write-Host "`n=== DETAILED RESULTS ===" -ForegroundColor Cyan
foreach ($result in $testResults) {
    $color = switch ($result.Status) {
        "PASS" { "Green" }
        "WARN" { "Yellow" }
        "FAIL" { "Red" }
    }
    Write-Host "$($result.Status): $($result.Name)" -ForegroundColor $color
}

# Save results to file
$testResults | ConvertTo-Json | Out-File "test_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"

Write-Host "`n✓ Results saved to test_results_*.json" -ForegroundColor Green


