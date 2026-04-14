#Requires -Version 5.1
<#
.SYNOPSIS
  Lightweight health probe for Voice or Earth-2 Legion. Intended for Task Scheduler every 10-15 minutes (not a tight loop).

.DESCRIPTION
  GETs localhost health endpoints. After $FailureThreshold consecutive failures, runs the corresponding Start-Legion*24x7 script
  to bring stacks back (idempotent: already-listening ports are skipped by those scripts).

  Run this ONLY on the Legion that owns the workload — not on the dev PC.

.EXAMPLE
  .\Invoke-LegionGPUWatchdog.ps1 -Role Voice
.EXAMPLE
  .\Invoke-LegionGPUWatchdog.ps1 -Role Earth2
#>
param(
    [ValidateSet('Voice', 'Earth2')]
    [string]$Role,
    [int]$FailureThreshold = 3,
    [int]$TimeoutSec = 8
)

$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$stateDir = Join-Path $env:USERPROFILE "MycosoftData\logs"
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Force -Path $stateDir | Out-Null }
$stateFile = Join-Path $stateDir "legion-watchdog-$Role.json"

if ($Role -eq 'Voice') {
    $healthUrl = "http://127.0.0.1:8999/health"
    $starter = Join-Path $here "Start-LegionVoice-24x7.ps1"
} else {
    $healthUrl = "http://127.0.0.1:8220/health"
    $starter = Join-Path $here "Start-LegionEarth2API-24x7.ps1"
}

function Read-State {
    if (-not (Test-Path $stateFile)) { return @{ consecutiveFailures = 0 } }
    try {
        $j = Get-Content -Raw -Path $stateFile | ConvertFrom-Json
        $n = 0
        if ($null -ne $j.consecutiveFailures) { $n = [int]$j.consecutiveFailures }
        return @{ consecutiveFailures = $n }
    } catch {
        return @{ consecutiveFailures = 0 }
    }
}

function Write-State($obj) {
    $obj | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
}

$ok = $false
try {
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec $TimeoutSec
    $ok = ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300)
} catch {
    $ok = $false
}

$st = Read-State
if ($ok) {
    $st.consecutiveFailures = 0
    Write-State $st
    Write-Host "$(Get-Date -Format o) watchdog $Role OK $healthUrl"
    exit 0
}

$st.consecutiveFailures = [int]$st.consecutiveFailures + 1
Write-State $st
Write-Warning "$(Get-Date -Format o) watchdog $Role FAIL ($($st.consecutiveFailures)/$FailureThreshold) $healthUrl"

if ([int]$st.consecutiveFailures -ge $FailureThreshold) {
    if (-not (Test-Path $starter)) {
        throw "Starter missing: $starter"
    }
    Write-Warning "Invoking recovery: $starter"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $starter
    $st.consecutiveFailures = 0
    Write-State $st
}
