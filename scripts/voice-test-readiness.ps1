# Voice Test Readiness - Automated check and checklist (Feb 17, 2026)
# Run from MAS repo. Starts what can be started locally, checks VMs, prints steps for 5090/gpu01.

param([switch]$StartLocalOnly)

$ErrorActionPreference = "Continue"
$masRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $masRoot

Write-Host "`n=== Voice test readiness ===" -ForegroundColor Cyan
Write-Host ""

# 1) Autostart (MycoBrain, Notion, Cursor Sync, n8n)
Write-Host "[1] Autostart services..." -ForegroundColor Yellow
& "$masRoot\scripts\autostart-healthcheck.ps1" -StartMissing 2>$null
Write-Host ""

# 2) Voice stack verification
Write-Host "[2] Voice stack (Moshi, Bridge, MAS, Website, GPU Node API)..." -ForegroundColor Yellow
& "$masRoot\scripts\voice-system-verify-and-start.ps1" 2>$null
Write-Host ""

# 3) Website dev on 3010
$webOk = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:3010" -UseBasicParsing -TimeoutSec 3
    $webOk = $r.StatusCode -eq 200
} catch {}
if (-not $webOk) {
    Write-Host "[3] Website dev (3010): DOWN - starting..." -ForegroundColor Yellow
    $webRoot = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
    if (Test-Path $webRoot) {
        Start-Process -FilePath "npm" -ArgumentList "run","dev:next-only" -WorkingDirectory $webRoot -WindowStyle Normal
        Start-Sleep -Seconds 5
    }
    Write-Host "    Wait for Next.js ready, then open http://localhost:3010/test-voice" -ForegroundColor Gray
} else {
    Write-Host "[3] Website dev (3010): OK" -ForegroundColor Green
}
Write-Host ""

# 4) Diagnostics snapshot
Write-Host "[4] Test-voice diagnostics snapshot:" -ForegroundColor Yellow
try {
    $diag = Invoke-RestMethod -Uri "http://localhost:3010/api/test-voice/diagnostics" -TimeoutSec 10
    foreach ($s in $diag.services) {
        $sym = if ($s.ok) { "[OK]" } else { "[--]" }
        Write-Host "    $sym $($s.name)" -ForegroundColor $(if ($s.ok) { "Green" } else { "Gray" })
    }
} catch {
    Write-Host "    (diagnostics unavailable - is website dev running on 3010?)" -ForegroundColor Gray
}
Write-Host ""

# 5) Single script for local voice (this PC)
Write-Host "=== Start entire voice system (this PC) ===" -ForegroundColor Cyan
Write-Host "  python scripts/start_voice_system.py" -ForegroundColor Green
Write-Host "  (Then open http://localhost:3010/test-voice and click Start MYCA Voice)" -ForegroundColor Gray
Write-Host ""
# GPU node / 5090 checklist (run on other machines)
Write-Host "=== Optional: GPU node / 5090 (run on other machines) ===" -ForegroundColor Cyan
Write-Host "On 5090 host:" -ForegroundColor White
Write-Host "  1. Start Moshi: .\scripts\run-moshi-docker-local.ps1 -Device cuda" -ForegroundColor Gray
Write-Host "  2. Tunnel: ssh -o ExitOnForwardFailure=yes -N -R 19198:127.0.0.1:8998 mycosoft@192.168.0.190" -ForegroundColor Gray
Write-Host "On gpu01: MOSHI_HOST=127.0.0.1 MOSHI_PORT=19198 python scripts/start_voice_system.py" -ForegroundColor Gray
Write-Host ""
