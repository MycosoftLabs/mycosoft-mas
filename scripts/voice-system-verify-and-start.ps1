# Voice System Verify and Start (Feb 13, 2026)
#
# Verifies and documents the full voice stack for test-voice:
# - 5090 dev PC: Moshi inference on :8998
# - SSH reverse tunnel: 5090 -> gpu01 so bridge can reach Moshi (gpu01 localhost:19198)
# - gpu01 (192.168.0.190): PersonaPlex Bridge on :8999
# - MAS (192.168.0.188:8001): consciousness, memory, voice session
# - Website dev: http://localhost:3010/test-voice
#
# Usage:
#   .\scripts\voice-system-verify-and-start.ps1           # verify only
#   .\scripts\voice-system-verify-and-start.ps1 -PrintCommands  # print start commands

param(
    [switch] $PrintCommands
)

$ErrorActionPreference = "Stop"

$masRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bridgeHealth = "http://192.168.0.190:8999/health"
$masHealth = "http://192.168.0.188:8001/health"
$moshiLocal = "http://localhost:8998/"
$diagnosticsUrl = "http://localhost:3010/api/test-voice/diagnostics"

function Test-Url {
    param([string]$Url, [int]$TimeoutSec = 5)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $r.StatusCode -in 200, 426
    } catch {
        return $false
    }
}

Write-Host "`n=== Voice system verification ===" -ForegroundColor Cyan
Write-Host ""

# 1) Moshi (local 5090)
$moshiOk = Test-Url $moshiLocal
Write-Host "  Moshi (localhost:8998)     : $(if ($moshiOk) { 'OK' } else { 'DOWN (start on 5090: run-moshi-docker-local.ps1 or native server)' })"

# 2) PersonaPlex Bridge (gpu01)
$bridgeOk = $false
try {
    $br = Invoke-RestMethod -Uri $bridgeHealth -TimeoutSec 5 -ErrorAction Stop
    $bridgeOk = $br.status -eq "healthy"
    $moshiAvail = $br.moshi_available
    Write-Host "  PersonaPlex Bridge (gpu01) : $(if ($bridgeOk) { 'OK' } else { 'DOWN' })  moshi_available=$moshiAvail"
} catch {
    Write-Host "  PersonaPlex Bridge (gpu01) : DOWN (start on gpu01 with MOSHI_PORT=19198 if using tunnel)"
}

# 3) MAS
$masOk = Test-Url $masHealth
Write-Host "  MAS (192.168.0.188:8001)    : $(if ($masOk) { 'OK' } else { 'DOWN' })"

# 4) Website diagnostics (optional)
$devOk = $false
try {
    $diag = Invoke-RestMethod -Uri $diagnosticsUrl -TimeoutSec 5 -ErrorAction Stop
    $devOk = $true
    $allOk = ($diag.services | Where-Object { $_.ok }).Count
    $total = $diag.services.Count
    Write-Host "  Website dev (3010)         : OK  (diagnostics: $allOk/$total services OK)"
} catch {
    Write-Host "  Website dev (3010)         : not checked (run npm run dev:next-only in WEBSITE/website)"
}

# 5) GPU Node API (MAS) - optional
$gpuNodeApiOk = $false
try {
    $gpuHealth = Invoke-RestMethod -Uri "http://192.168.0.188:8001/api/gpu-node/health" -TimeoutSec 5 -ErrorAction Stop
    $gpuNodeApiOk = $gpuHealth.status -eq "healthy"
    Write-Host "  GPU Node API (MAS /api/gpu-node): $(if ($gpuNodeApiOk) { 'OK' } else { 'unexpected response' })"
} catch {
    Write-Host "  GPU Node API (MAS /api/gpu-node): not available (restart MAS on 188 to enable; see docs/GPU_NODE_INTEGRATION_FEB13_2026.md)"
}

Write-Host ""

if ($PrintCommands) {
    Write-Host "=== Commands to start the voice stack ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1) On 5090 host - start Moshi (Docker or native):" -ForegroundColor Yellow
    Write-Host "   .\scripts\run-moshi-docker-local.ps1 -Device cuda"
    Write-Host "   Or native: TORCHDYNAMO_DISABLE=1 python ... (see docs)"
    Write-Host ""
    Write-Host "2) On 5090 host - SSH reverse tunnel (keep this running):" -ForegroundColor Yellow
    Write-Host "   ssh -o ExitOnForwardFailure=yes -N -R 19198:127.0.0.1:8998 mycosoft@192.168.0.190"
    Write-Host "   (If 19198 is in use, use another port e.g. 19298 and set MOSHI_PORT on gpu01)"
    Write-Host ""
    Write-Host "3) On gpu01 - start PersonaPlex Bridge:" -ForegroundColor Yellow
    Write-Host "   cd ~/mycosoft-mas && source .venv/bin/activate"
    Write-Host "   export MOSHI_HOST=127.0.0.1 MOSHI_PORT=19198 MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001"
    Write-Host "   python services/personaplex-local/personaplex_bridge_nvidia.py"
    Write-Host "   (Or nohup ... & and tail -f personaplex_bridge.log)"
    Write-Host ""
    Write-Host "4) Website dev (this PC):" -ForegroundColor Yellow
    Write-Host "   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
    Write-Host "   npm run dev:next-only"
    Write-Host "   Open: http://localhost:3010/test-voice"
    Write-Host ""
}

# Summary
$allCritical = $bridgeOk -and $masOk
if (-not $allCritical) {
    Write-Host "Some services are down. Use -PrintCommands to see start commands." -ForegroundColor Gray
    exit 1
}
Write-Host "Voice stack verification done." -ForegroundColor Green
exit 0
