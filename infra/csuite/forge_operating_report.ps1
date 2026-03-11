# Forge Operating Report — Status Summary to MAS
# Date: March 8, 2026
# Runs on CTO VM 194. Sends operating_status report to C-Suite API.
# Scheduled every 10 min for MYCA/Morgan visibility.

param([switch]$Silent)

$ErrorActionPreference = "SilentlyContinue"
$MasUrl = $env:MAS_API_URL; if (-not $MasUrl) { $MasUrl = "http://192.168.0.188:8001" }
$CodeRoot = $env:CTO_CODE_ROOT; if (-not $CodeRoot) { $CodeRoot = "C:\Users\$env:USERNAME\Mycosoft\CODE" }

$cursorRunning = (Get-Process -Name "Cursor","Code" -ErrorAction SilentlyContinue).Count -gt 0
$openclawRunning = (Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "openclaw" }).Count -gt 0
$MasRepo = Join-Path $CodeRoot "MAS\mycosoft-mas"
$workspaceOk = Test-Path (Join-Path $MasRepo ".git")
$rulesCount = 0
$agentsCount = 0
$cursorUser = Join-Path $env:USERPROFILE ".cursor"
if (Test-Path (Join-Path $cursorUser "rules")) { $rulesCount = (Get-ChildItem (Join-Path $cursorUser "rules") -Filter "*.mdc" -ErrorAction SilentlyContinue).Count }
if (Test-Path (Join-Path $cursorUser "agents")) { $agentsCount = (Get-ChildItem (Join-Path $cursorUser "agents") -Filter "*.md" -ErrorAction SilentlyContinue).Count }

$summary = "Cursor=$cursorRunning OpenClaw=$openclawRunning Workspace=$workspaceOk Rules=$rulesCount Agents=$agentsCount"
$details = @{
    cursor_running = $cursorRunning
    openclaw_running = $openclawRunning
    workspace_ok = $workspaceOk
    rules_count = $rulesCount
    agents_count = $agentsCount
    code_root = $CodeRoot
} | ConvertTo-Json -Compress

$body = @{
    role = "CTO"
    assistant_name = "Forge"
    report_type = "operating_status"
    summary = $summary
    details = $details
    escalated = $false
} | ConvertTo-Json -Depth 5

try {
    Invoke-RestMethod -Uri "$MasUrl/api/csuite/report" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 | Out-Null
    if (-not $Silent) { Write-Host "[Forge] Operating report sent" -ForegroundColor Green }
} catch {
    if (-not $Silent) { Write-Warning "[Forge] Report failed: $_" }
}
