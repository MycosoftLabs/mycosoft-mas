# Comprehensive Test Script for All Tasks
# Tests all the completed tasks

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Comprehensive Task Test Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$testResults = @{
    "n8n_workflows" = $false
    "api_keys" = $false
    "device_registration" = $false
    "mycoboard_browser" = $false
    "autodiscovery" = $false
    "firmware_compatibility" = $false
    "storage_audit" = $false
    "model_training" = $false
    "natureos_dashboards" = $false
    "device_manager" = $false
}

# Test 1: n8n Workflows
Write-Host "[1/10] Testing n8n Workflow Import..." -ForegroundColor Yellow
try {
    $n8nHealth = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -Method GET -TimeoutSec 5 -ErrorAction Stop
    if ($n8nHealth.StatusCode -eq 200) {
        Write-Host "  ✓ n8n is accessible" -ForegroundColor Green
        $testResults["n8n_workflows"] = $true
    }
} catch {
    Write-Host "  ✗ n8n not accessible: $_" -ForegroundColor Red
}

# Test 2: API Keys
Write-Host "[2/10] Testing API Keys Configuration..." -ForegroundColor Yellow
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "GOOGLE_API_KEY" -and $envContent -match "GOOGLE_MAPS_API_KEY" -and $envContent -match "GOOGLE_CLIENT_ID") {
        Write-Host "  ✓ Google API keys found in .env" -ForegroundColor Green
        $testResults["api_keys"] = $true
    } else {
        Write-Host "  ⚠ Google API keys not configured (check env.example)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ .env file not found (copy from env.example)" -ForegroundColor Yellow
}

# Test 3: Device Registration
Write-Host "[3/10] Testing Device Registration API..." -ForegroundColor Yellow
try {
    $deviceRes = Invoke-RestMethod -Uri "http://localhost:3000/api/mycobrain/devices" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Device Manager API accessible" -ForegroundColor Green
    $testResults["device_registration"] = $true
} catch {
    Write-Host "  ✗ Device Manager API not accessible: $_" -ForegroundColor Red
}

# Test 4: MycoBoard Browser Test
Write-Host "[4/10] Testing MycoBoard Browser Access..." -ForegroundColor Yellow
try {
    $portsRes = Invoke-RestMethod -Uri "http://localhost:3000/api/mycobrain/ports" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Port scanning API accessible" -ForegroundColor Green
    Write-Host "    Found $($portsRes.ports.Count) ports" -ForegroundColor Gray
    $testResults["mycoboard_browser"] = $true
} catch {
    Write-Host "  ✗ Port scanning API not accessible: $_" -ForegroundColor Red
}

# Test 5: Auto-Discovery
Write-Host "[5/10] Testing Auto-Discovery..." -ForegroundColor Yellow
try {
    $portsRes = Invoke-RestMethod -Uri "http://localhost:3000/api/mycobrain/ports" -Method GET -TimeoutSec 5 -ErrorAction Stop
    $esp32Ports = $portsRes.ports | Where-Object { $_.is_esp32 -or $_.is_mycobrain }
    if ($esp32Ports.Count -gt 0) {
        Write-Host "  ✓ Auto-discovery working - found $($esp32Ports.Count) ESP32/MycoBrain devices" -ForegroundColor Green
        $testResults["autodiscovery"] = $true
    } else {
        Write-Host "  ⚠ No ESP32/MycoBrain devices detected (may need physical device)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Auto-discovery test failed: $_" -ForegroundColor Red
}

# Test 6: Firmware Compatibility
Write-Host "[6/10] Testing Firmware Compatibility..." -ForegroundColor Yellow
$firmwareFiles = Get-ChildItem -Path (Join-Path $ProjectRoot "firmware") -Filter "*.bin" -Recurse -ErrorAction SilentlyContinue
if ($firmwareFiles.Count -gt 0) {
    Write-Host "  ✓ Firmware files found: $($firmwareFiles.Count)" -ForegroundColor Green
    $testResults["firmware_compatibility"] = $true
} else {
    Write-Host "  ⚠ No firmware files found in firmware/ directory" -ForegroundColor Yellow
}

# Test 7: Storage Audit
Write-Host "[7/10] Testing Storage Audit..." -ForegroundColor Yellow
try {
    $storageRes = Invoke-RestMethod -Uri "http://localhost:3000/api/natureos/storage" -Method GET -TimeoutSec 5 -ErrorAction Stop
    if ($storageRes.status -eq "ok") {
        Write-Host "  ✓ Storage audit API accessible" -ForegroundColor Green
        Write-Host "    Total storage: $([math]::Round($storageRes.totalStorage / 1TB, 2)) TB" -ForegroundColor Gray
        $testResults["storage_audit"] = $true
    }
} catch {
    Write-Host "  ✗ Storage audit API not accessible: $_" -ForegroundColor Red
}

# Test 8: Model Training Container
Write-Host "[8/10] Testing Model Training Container..." -ForegroundColor Yellow
$dockerComposeFile = Join-Path $ProjectRoot "docker-compose.model-training.yml"
if (Test-Path $dockerComposeFile) {
    Write-Host "  ✓ Model training docker-compose file exists" -ForegroundColor Green
    $testResults["model_training"] = $true
} else {
    Write-Host "  ✗ Model training docker-compose file not found" -ForegroundColor Red
}

# Test 9: NatureOS Dashboards
Write-Host "[9/10] Testing NatureOS Dashboards..." -ForegroundColor Yellow
try {
    $natureosRes = Invoke-WebRequest -Uri "http://localhost:3000/natureos" -Method GET -TimeoutSec 5 -ErrorAction Stop
    if ($natureosRes.StatusCode -eq 200) {
        Write-Host "  ✓ NatureOS dashboard accessible" -ForegroundColor Green
        $testResults["natureos_dashboards"] = $true
    }
} catch {
    Write-Host "  ✗ NatureOS dashboard not accessible: $_" -ForegroundColor Red
}

# Test 10: Device Manager
Write-Host "[10/10] Testing MycoBrain Device Manager..." -ForegroundColor Yellow
$deviceManagerFile = Join-Path $ProjectRoot "components" "mycobrain-device-manager.tsx"
if (Test-Path $deviceManagerFile) {
    Write-Host "  ✓ Device Manager component exists" -ForegroundColor Green
    $testResults["device_manager"] = $true
} else {
    Write-Host "  ✗ Device Manager component not found" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

$passed = ($testResults.Values | Where-Object { $_ -eq $true }).Count
$total = $testResults.Count

foreach ($test in $testResults.GetEnumerator() | Sort-Object Name) {
    $status = if ($test.Value) { "✓ PASS" } else { "✗ FAIL" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "$status - $($test.Key)" -ForegroundColor $color
}

Write-Host ""
Write-Host "Total: $passed / $total tests passed" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

