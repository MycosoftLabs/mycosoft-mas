# Final System Test Script
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

Write-Host "=== MYCOSOFT FINAL SYSTEM TEST ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Core Services
Write-Host "[Test 1] Core Services Health" -ForegroundColor Yellow
$services = @(
    @{Name="MINDEX"; Port=8000; Endpoint="/api/mindex/health"},
    @{Name="MycoBrain"; Port=8003; Endpoint="/health"},
    @{Name="MAS Orchestrator"; Port=8001; Endpoint="/health"},
    @{Name="n8n"; Port=5678; Endpoint="/healthz"}
)

foreach ($svc in $services) {
    try {
        $result = Invoke-RestMethod "http://localhost:$($svc.Port)$($svc.Endpoint)" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  ✓ $($svc.Name) ($($svc.Port)): ONLINE" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $($svc.Name) ($($svc.Port)): OFFLINE" -ForegroundColor Red
    }
}

# Test 2: MycoBrain Hardware
Write-Host "`n[Test 2] MycoBrain Hardware" -ForegroundColor Yellow
try {
    $devices = Invoke-RestMethod http://localhost:8003/devices -ErrorAction Stop
    if ($devices.count -gt 0) {
        $dev = $devices.devices[0]
        Write-Host "  ✓ Device: $($dev.device_id)" -ForegroundColor Green
        Write-Host "    Port: $($dev.port)" -ForegroundColor Gray
        Write-Host "    Firmware: $($dev.info.firmware)" -ForegroundColor Gray
        Write-Host "    Status: $($dev.status)" -ForegroundColor Gray
    } else {
        Write-Host "  ✗ No devices connected" -ForegroundColor Red
    }
} catch {
    Write-Host "  ✗ Failed to get devices" -ForegroundColor Red
}

# Test 3: Website
Write-Host "`n[Test 3] Website Status" -ForegroundColor Yellow
try {
    $web = Invoke-WebRequest http://localhost:3000 -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✓ Website (3000): HTTP $($web.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Website (3000): OFFLINE" -ForegroundColor Red
}

# Test 4: API Endpoints
Write-Host "`n[Test 4] Critical API Endpoints" -ForegroundColor Yellow
$apis = @(
    "/api/mycobrain/devices",
    "/api/mycobrain/ports",
    "/api/mindex/stats"
)

foreach ($api in $apis) {
    try {
        $result = Invoke-WebRequest "http://localhost:3000$api" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✓ $api : HTTP $($result.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $api : HTTP $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
}

# Summary
Write-Host "`n=== SYSTEM READY ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Website: http://localhost:3000" -ForegroundColor White
Write-Host "Device Manager: http://localhost:3000/natureos/devices" -ForegroundColor White
Write-Host "MINDEX: http://localhost:8000" -ForegroundColor White
Write-Host "MAS: http://localhost:8001" -ForegroundColor White
Write-Host "MYCA Dashboard: http://localhost:3100" -ForegroundColor White
Write-Host ""

