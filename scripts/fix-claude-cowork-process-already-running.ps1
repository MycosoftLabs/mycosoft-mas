# fix-claude-cowork-process-already-running.ps1
# Fix: "RPC error -1: process with name 'nifty-trusting-gauss' already running"
# Stale Cowork VM session didn't shut down; we kill processes and restart the service.
# MAR06 2026
#
# Run from MAS repo. Steps 2-4 require Administrator.

param([switch]$SkipCacheClear)

$ErrorActionPreference = "Continue"

Write-Host "=== Fix: Cowork 'process already running' ===" -ForegroundColor Cyan
Write-Host ""

# 1. Kill Claude processes
Write-Host "1. Stopping Claude Desktop..." -ForegroundColor Yellow
$claudeProcs = Get-Process -Name "Claude" -ErrorAction SilentlyContinue
if ($claudeProcs) {
    $claudeProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "   Stopped $($claudeProcs.Count) Claude process(es)." -ForegroundColor Green
} else {
    Write-Host "   No Claude process found (already closed)." -ForegroundColor Gray
}

# Also kill claude-code, cowork-related
foreach ($name in @("claude-code", "CoworkVM", "cowork")) {
    $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "   Stopped $name process(es)." -ForegroundColor Green
    }
}

Start-Sleep -Seconds 2

# 2. Restart Cowork VM service (needs Admin)
Write-Host ""
Write-Host "2. Restarting CoworkVMService..." -ForegroundColor Yellow
$svc = Get-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
if ($svc) {
    try {
        Stop-Service -Name "CoworkVMService" -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
        Start-Service -Name "CoworkVMService" -ErrorAction Stop
        Write-Host "   Service restarted." -ForegroundColor Green
    } catch {
        Write-Host "   FAILED (run as Administrator): $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "   In an elevated PowerShell: Restart-Service CoworkVMService -Force" -ForegroundColor Yellow
    }
} else {
    Write-Host "   CoworkVMService not found." -ForegroundColor Red
}

# 3. Clear VM bundle/cache (clears stale session names)
if (-not $SkipCacheClear) {
    Write-Host ""
    Write-Host "3. Clearing VM cache (removes stale session state)..." -ForegroundColor Yellow
    $bundlePath = "$env:APPDATA\Claude\vm_bundles"
    $vmPath = "$env:LOCALAPPDATA\Claude\claude-code-vm"
    $coworkPath = "$env:APPDATA\Claude\cowork"
    $cleared = $false
    foreach ($p in @($bundlePath, $vmPath, $coworkPath)) {
        if (Test-Path $p) {
            Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue
            Write-Host "   Removed $p" -ForegroundColor Green
            $cleared = $true
        }
    }
    if (-not $cleared) {
        Write-Host "   No cache folders found." -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "3. Skipped cache clear (use without -SkipCacheClear to clear)." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Done. Reopen Claude Desktop and try Cowork again." -ForegroundColor Green
Write-Host "If it still fails, run as Administrator." -ForegroundColor Yellow
