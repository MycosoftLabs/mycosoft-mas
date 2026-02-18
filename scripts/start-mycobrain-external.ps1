# Start MycoBrain Service in an EXTERNAL window (not tied to Cursor)
# Feb 18, 2026 - Services run independently; close Cursor anytime.
# Double-click or run: powershell -ExecutionPolicy Bypass -File start-mycobrain-external.ps1

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$ServiceScript = Join-Path $RepoRoot "services\mycobrain\mycobrain_service_standalone.py"

Set-Location $RepoRoot

Write-Host "=== MycoBrain Service (External) ===" -ForegroundColor Cyan
Write-Host "Port: 8003 | URL: http://localhost:8003" -ForegroundColor Gray
Write-Host "This window will stay open. Close it to stop the service." -ForegroundColor Gray
Write-Host ""

python $ServiceScript
