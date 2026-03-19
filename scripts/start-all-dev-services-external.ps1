# Start MycoBrain + Website Dev Server in EXTERNAL windows (not tied to Cursor)
# Feb 18, 2026 - Both run independently; close Cursor anytime.
# Double-click or run: powershell -ExecutionPolicy Bypass -File start-all-dev-services-external.ps1

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$WebsiteRoot = (Resolve-Path (Join-Path $RepoRoot "..\..\WEBSITE\website") -ErrorAction SilentlyContinue).Path
if (-not $WebsiteRoot) { $WebsiteRoot = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website" }

Write-Host "=== Starting Dev Services (External Windows) ===" -ForegroundColor Cyan
Write-Host ""

# 1. MycoBrain Service (hidden)
$mycoScript = Join-Path $ScriptRoot "start-mycobrain-external.ps1"
Write-Host "[1/2] Starting MycoBrain Service (port 8003)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", "`"$mycoScript`"" -WorkingDirectory $RepoRoot -WindowStyle Hidden

Start-Sleep -Seconds 2

# 2. Website Dev Server (hidden)
$devScript = Join-Path $WebsiteRoot "scripts\start-dev-external.ps1"
if (Test-Path $devScript) {
    Write-Host "[2/2] Starting Website Dev Server (port 3010)..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", "`"$devScript`"" -WorkingDirectory $WebsiteRoot -WindowStyle Hidden
} else {
    Write-Host "[2/2] Dev script not found, starting npm directly..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", "cd `"$WebsiteRoot`"; npm run dev:next-only" -WindowStyle Hidden
}

Write-Host ""
Write-Host "Done. Two services started (running in background):" -ForegroundColor Cyan
Write-Host "  - MycoBrain: http://localhost:8003" -ForegroundColor Gray
Write-Host "  - Website:   http://localhost:3010" -ForegroundColor Gray
Write-Host ""
Write-Host "Close this window. Services run in background (no visible windows)." -ForegroundColor Gray
