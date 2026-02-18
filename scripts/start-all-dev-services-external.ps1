# Start MycoBrain + Website Dev Server in EXTERNAL windows (not tied to Cursor)
# Feb 18, 2026 - Both run independently; close Cursor anytime.
# Double-click or run: powershell -ExecutionPolicy Bypass -File start-all-dev-services-external.ps1

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$WebsiteRoot = (Resolve-Path (Join-Path $RepoRoot "..\..\WEBSITE\website") -ErrorAction SilentlyContinue).Path
if (-not $WebsiteRoot) { $WebsiteRoot = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website" }

Write-Host "=== Starting Dev Services (External Windows) ===" -ForegroundColor Cyan
Write-Host ""

# 1. MycoBrain Service (new window)
$mycoScript = Join-Path $ScriptRoot "start-mycobrain-external.ps1"
Write-Host "[1/2] Opening MycoBrain Service (port 8003)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$mycoScript`"" -WorkingDirectory $RepoRoot

Start-Sleep -Seconds 2

# 2. Website Dev Server (new window)
$devScript = Join-Path $WebsiteRoot "scripts\start-dev-external.ps1"
if (Test-Path $devScript) {
    Write-Host "[2/2] Opening Website Dev Server (port 3010)..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$devScript`"" -WorkingDirectory $WebsiteRoot
} else {
    Write-Host "[2/2] Dev script not found, starting npm directly..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$WebsiteRoot`"; npm run dev:next-only"
}

Write-Host ""
Write-Host "Done. Two windows opened:" -ForegroundColor Cyan
Write-Host "  - MycoBrain: http://localhost:8003" -ForegroundColor Gray
Write-Host "  - Website:   http://localhost:3010" -ForegroundColor Gray
Write-Host ""
Write-Host "Close this window. Services run in their own windows." -ForegroundColor Gray
