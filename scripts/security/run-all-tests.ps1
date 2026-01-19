# Mycosoft SOC - Master Test Script
# Usage: .\run-all-tests.ps1 [-Environment dev|sandbox] [-BaseUrl http://...]

param(
    [string]$Environment = "dev",
    [string]$BaseUrl = ""
)

# Set base URL based on environment
if ($BaseUrl -eq "") {
    switch ($Environment) {
        "dev" { $BaseUrl = "http://localhost:3000" }
        "sandbox" { $BaseUrl = "https://sandbox.mycosoft.com" }
        default { $BaseUrl = "http://localhost:3000" }
    }
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          MYCOSOFT SOC TEST SUITE v2.0                      ║" -ForegroundColor Cyan
Write-Host "║          Security Operations Center Validation              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Environment: $Environment" -ForegroundColor White
Write-Host "  Base URL:    $BaseUrl" -ForegroundColor White
Write-Host "  Timestamp:   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
Write-Host ""
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

$passed = 0
$failed = 0
$results = @()

# Helper function for testing endpoints
function Test-Endpoint {
    param(
        [string]$TestId,
        [string]$Name,
        [string]$Url,
        [string]$ExpectedProperty,
        [int]$TimeoutSec = 10
    )
    
    $result = @{
        TestId = $TestId
        Name = $Name
        Status = "UNKNOWN"
        Duration = 0
        Error = ""
    }
    
    Write-Host -NoNewline "  [$TestId] $Name... "
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        $resp = Invoke-RestMethod $Url -TimeoutSec $TimeoutSec
        $stopwatch.Stop()
        $result.Duration = $stopwatch.ElapsedMilliseconds
        
        if ($ExpectedProperty -eq "*" -or $null -ne $resp.$ExpectedProperty -or $resp -is [array]) {
            Write-Host "PASS" -ForegroundColor Green -NoNewline
            Write-Host " (${($result.Duration)}ms)" -ForegroundColor DarkGray
            $result.Status = "PASS"
            return $result
        } else {
            Write-Host "FAIL" -ForegroundColor Red -NoNewline
            Write-Host " - missing property: $ExpectedProperty" -ForegroundColor DarkGray
            $result.Status = "FAIL"
            $result.Error = "Missing property: $ExpectedProperty"
            return $result
        }
    } catch {
        $stopwatch.Stop()
        $result.Duration = $stopwatch.ElapsedMilliseconds
        Write-Host "FAIL" -ForegroundColor Red -NoNewline
        Write-Host " - $($_.Exception.Message)" -ForegroundColor DarkGray
        $result.Status = "FAIL"
        $result.Error = $_.Exception.Message
        return $result
    }
}

# Helper function for testing pages
function Test-Page {
    param(
        [string]$TestId,
        [string]$Name,
        [string]$Path,
        [int]$TimeoutSec = 15
    )
    
    $result = @{
        TestId = $TestId
        Name = $Name
        Status = "UNKNOWN"
        Duration = 0
        Error = ""
    }
    
    Write-Host -NoNewline "  [$TestId] $Name... "
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        $resp = Invoke-WebRequest "$BaseUrl$Path" -TimeoutSec $TimeoutSec
        $stopwatch.Stop()
        $result.Duration = $stopwatch.ElapsedMilliseconds
        
        if ($resp.StatusCode -eq 200) {
            Write-Host "PASS" -ForegroundColor Green -NoNewline
            Write-Host " (${($result.Duration)}ms)" -ForegroundColor DarkGray
            $result.Status = "PASS"
            return $result
        } else {
            Write-Host "FAIL" -ForegroundColor Red -NoNewline
            Write-Host " - Status: $($resp.StatusCode)" -ForegroundColor DarkGray
            $result.Status = "FAIL"
            $result.Error = "HTTP Status: $($resp.StatusCode)"
            return $result
        }
    } catch {
        $stopwatch.Stop()
        $result.Duration = $stopwatch.ElapsedMilliseconds
        Write-Host "FAIL" -ForegroundColor Red -NoNewline
        Write-Host " - $($_.Exception.Message)" -ForegroundColor DarkGray
        $result.Status = "FAIL"
        $result.Error = $_.Exception.Message
        return $result
    }
}

# ═══════════════════════════════════════════════════════════════
# SECTION 1: SECURITY API TESTS
# ═══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "┌─ SECURITY API TESTS ─────────────────────────────────────┐" -ForegroundColor Yellow

$r = Test-Endpoint "API-001" "Security Status" "$BaseUrl/api/security?action=status" "status"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "API-002" "Authorized Users" "$BaseUrl/api/security?action=users" "users"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "API-003" "Security Events" "$BaseUrl/api/security?action=events" "events"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "API-004" "Incidents List" "$BaseUrl/api/security?action=incidents" "incidents"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "API-005" "Playbooks List" "$BaseUrl/api/security?action=playbooks" "playbooks"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

Write-Host "└──────────────────────────────────────────────────────────┘" -ForegroundColor Yellow

# ═══════════════════════════════════════════════════════════════
# SECTION 2: GEO-IP TESTS
# ═══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "┌─ GEO-IP LOOKUP TESTS ────────────────────────────────────┐" -ForegroundColor Yellow

$r = Test-Endpoint "GEO-001" "US IP (8.8.8.8)" "$BaseUrl/api/security?action=geo-lookup&ip=8.8.8.8" "ip"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "GEO-002" "Cloudflare IP (1.1.1.1)" "$BaseUrl/api/security?action=geo-lookup&ip=1.1.1.1" "ip"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

Write-Host "└──────────────────────────────────────────────────────────┘" -ForegroundColor Yellow

# ═══════════════════════════════════════════════════════════════
# SECTION 3: UNIFI API TESTS
# ═══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "┌─ UNIFI API TESTS ────────────────────────────────────────┐" -ForegroundColor Yellow

$r = Test-Endpoint "UNI-001" "UniFi Dashboard" "$BaseUrl/api/unifi?action=dashboard" "wan"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "UNI-002" "Network Devices" "$BaseUrl/api/unifi?action=devices" "devices"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "UNI-003" "Connected Clients" "$BaseUrl/api/unifi?action=clients" "clients"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "UNI-004" "Traffic Stats" "$BaseUrl/api/unifi?action=traffic" "*"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "UNI-005" "Recent Alarms" "$BaseUrl/api/unifi?action=alarms" "alarms"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Endpoint "UNI-006" "WiFi Networks" "$BaseUrl/api/unifi?action=wlans" "wlans"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

Write-Host "└──────────────────────────────────────────────────────────┘" -ForegroundColor Yellow

# ═══════════════════════════════════════════════════════════════
# SECTION 4: PAGE LOAD TESTS
# ═══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "┌─ PAGE LOAD TESTS ────────────────────────────────────────┐" -ForegroundColor Yellow

$r = Test-Page "PAGE-001" "SOC Dashboard" "/security"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Page "PAGE-002" "Network Monitor" "/security/network"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Page "PAGE-003" "Incident Management" "/security/incidents"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Page "PAGE-004" "Red Team Operations" "/security/redteam"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

$r = Test-Page "PAGE-005" "Compliance & Audit" "/security/compliance"
$results += $r; if ($r.Status -eq "PASS") { $passed++ } else { $failed++ }

Write-Host "└──────────────────────────────────────────────────────────┘" -ForegroundColor Yellow

# ═══════════════════════════════════════════════════════════════
# RESULTS SUMMARY
# ═══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    TEST RESULTS SUMMARY                     ║" -ForegroundColor Cyan
Write-Host "╠════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan

$total = $passed + $failed
$passRate = if ($total -gt 0) { [math]::Round(($passed / $total) * 100, 1) } else { 0 }

if ($passRate -ge 90) {
    $statusColor = "Green"
    $status = "EXCELLENT"
} elseif ($passRate -ge 70) {
    $statusColor = "Yellow"
    $status = "ACCEPTABLE"
} else {
    $statusColor = "Red"
    $status = "NEEDS ATTENTION"
}

Write-Host "║                                                            ║" -ForegroundColor Cyan
Write-Host ("║  Passed:     {0,4}                                          ║" -f $passed) -ForegroundColor Green
Write-Host ("║  Failed:     {0,4}                                          ║" -f $failed) -ForegroundColor Red
Write-Host ("║  Total:      {0,4}                                          ║" -f $total) -ForegroundColor White
Write-Host "║                                                            ║" -ForegroundColor Cyan
Write-Host ("║  Pass Rate:  {0,5}%   [{1}]                      ║" -f $passRate, $status) -ForegroundColor $statusColor
Write-Host "║                                                            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Show failed tests if any
if ($failed -gt 0) {
    Write-Host ""
    Write-Host "┌─ FAILED TESTS ───────────────────────────────────────────┐" -ForegroundColor Red
    foreach ($r in $results | Where-Object { $_.Status -eq "FAIL" }) {
        Write-Host "  [$($r.TestId)] $($r.Name)" -ForegroundColor Red
        Write-Host "    Error: $($r.Error)" -ForegroundColor DarkGray
    }
    Write-Host "└──────────────────────────────────────────────────────────┘" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test run completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

# Exit with appropriate code
if ($failed -gt 0) {
    exit 1
} else {
    exit 0
}
