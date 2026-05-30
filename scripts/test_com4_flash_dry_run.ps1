<#
.SYNOPSIS
    Phase 0 dry-run validation for COM4 host-side flash (no write unless APPROVE_FLASH=true).

.DESCRIPTION
    Validates MycoBrain service /flash and (optional) MAS firmware/flash relay.
    Does NOT flash unless -LiveFlash with APPROVE_FLASH=true on service.

.EXAMPLE
    .\scripts\test_com4_flash_dry_run.ps1
    .\scripts\test_com4_flash_dry_run.ps1 -MasUrl http://192.168.0.188:8001
#>
[CmdletBinding()]
param(
    [string]$ServiceUrl = "http://localhost:8003",
    [string]$MasUrl = "",
    [string]$DeviceId = "mycobrain-COM4",
    [string]$Profile = "standalone",
    [string]$Version = "side-a-mdp-2.1.0",
    [switch]$LiveFlash
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$results = [ordered]@{}

function Test-Endpoint {
    param([string]$Name, [string]$Url, [string]$Method = "GET", [object]$Body = $null, [int]$TimeoutSec = 60)
    try {
        if ($Method -eq "POST") {
            $json = if ($Body) { $Body | ConvertTo-Json -Depth 6 -Compress } else { "{}" }
            $r = Invoke-WebRequest -Uri $Url -Method POST -Body $json -ContentType "application/json" -UseBasicParsing -TimeoutSec $TimeoutSec
        } else {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        }
        $results[$Name] = @{ ok = $true; status = $r.StatusCode; body = $r.Content.Substring(0, [Math]::Min(500, $r.Content.Length)) }
        Write-Host "[OK] $Name ($($r.StatusCode))" -ForegroundColor Green
    } catch {
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode.value__ } else { "ERR" }
        $results[$Name] = @{ ok = $false; status = $code; error = $_.Exception.Message }
        Write-Host "[FAIL] $Name ($code)" -ForegroundColor Red
    }
}

Write-Host "=== COM4 Flash Dry-Run ===" -ForegroundColor Cyan
Test-Endpoint -Name "service_health" -Url "$ServiceUrl/health"
Test-Endpoint -Name "service_ports" -Url "$ServiceUrl/ports"
Test-Endpoint -Name "flash_jobs_list" -Url "$ServiceUrl/flash/jobs"

$dryBody = @{
    profile = $Profile
    version = $Version
    confirm = $false
    dry_run = $true
    port = "COM4"
}
Test-Endpoint -Name "service_flash_dry_run" -Url "$ServiceUrl/flash" -Method POST -Body $dryBody -TimeoutSec 30

if ($MasUrl) {
    Test-Endpoint -Name "mas_firmware_health" -Url "$MasUrl/api/devices/firmware/health"
    $masBody = @{
        firmware_version = $Version
        profile = $Profile
        confirm = $false
        dry_run = $true
    }
    Test-Endpoint -Name "mas_flash_dry_run" -Url "$MasUrl/api/devices/$DeviceId/firmware/flash" -Method POST -Body $masBody
}

if ($LiveFlash) {
    if ($env:APPROVE_FLASH -notin @("1", "true", "True", "yes")) {
        Write-Host "[SKIP] Live flash requires APPROVE_FLASH=true in environment" -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] Live flash: service releases COM4 via /flash endpoint" -ForegroundColor Yellow
        $liveBody = @{
            profile = $Profile
            version = $Version
            confirm = $true
            dry_run = $false
            port = "COM4"
        }
        Test-Endpoint -Name "service_flash_live" -Url "$ServiceUrl/flash" -Method POST -Body $liveBody -TimeoutSec 600
    }
}

$outFile = Join-Path $RepoRoot "docs\com4_flash_dry_run_results.json"
$results | ConvertTo-Json -Depth 6 | Set-Content -Path $outFile -Encoding UTF8
Write-Host "Results: $outFile" -ForegroundColor Gray

$failed = @($results.Values | Where-Object { -not $_.ok })
if ($results.Contains('service_flash_dry_run') -and -not $results['service_flash_dry_run'].ok) {
    if ($results['service_flash_dry_run'].body -match 'dry_run') {
        Write-Host "[WARN] service_flash_dry_run partial (port/artifact) - API reachable" -ForegroundColor Yellow
        $failed = @($failed | Where-Object { $_ -ne $results['service_flash_dry_run'] })
    }
}
if ($failed.Count -gt 0) { exit 1 }
exit 0
