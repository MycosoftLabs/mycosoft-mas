# Mycosoft SOC - Quick Smoke Test
# Usage: .\smoke-test.ps1 [-BaseUrl http://...]
# Purpose: Quick verification that core services are responding

param(
    [string]$BaseUrl = "http://localhost:3000"
)

Write-Host ""
Write-Host "🔥 MYCOSOFT SOC SMOKE TEST" -ForegroundColor Cyan
Write-Host "   Testing: $BaseUrl" -ForegroundColor DarkGray
Write-Host ""

$passed = 0
$failed = 0

$tests = @(
    @{ Name = "Security API Status"; Url = "/api/security?action=status" },
    @{ Name = "Security API Users"; Url = "/api/security?action=users" },
    @{ Name = "UniFi API Dashboard"; Url = "/api/unifi?action=dashboard" },
    @{ Name = "SOC Dashboard Page"; Url = "/security" },
    @{ Name = "Network Monitor Page"; Url = "/security/network" }
)

foreach ($test in $tests) {
    Write-Host -NoNewline "  $($test.Name)... "
    try {
        $resp = Invoke-WebRequest "$BaseUrl$($test.Url)" -TimeoutSec 10 -UseBasicParsing
        if ($resp.StatusCode -eq 200) {
            Write-Host "✅" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "❌ ($($resp.StatusCode))" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host "❌" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "─────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Passed: $passed | Failed: $failed" -ForegroundColor White

if ($failed -eq 0) {
    Write-Host ""
    Write-Host "  ✅ SMOKE TEST PASSED" -ForegroundColor Green
    Write-Host ""
    exit 0
} else {
    Write-Host ""
    Write-Host "  ❌ SMOKE TEST FAILED" -ForegroundColor Red
    Write-Host ""
    exit 1
}
