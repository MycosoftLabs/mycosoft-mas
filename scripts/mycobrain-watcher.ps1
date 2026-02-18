# MycoBrain Service Watcher - Feb 18, 2026
# Watches mycobrain service files and restarts the service immediately on change.
# Run alongside dev-server-watchdog. Keeps MycoBrain always on and hot-reloads on edit.
# Usage: .\scripts\mycobrain-watcher.ps1
# Or: Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File scripts\mycobrain-watcher.ps1" -WindowStyle Hidden

$ErrorActionPreference = "Continue"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$ServiceDir = Join-Path $RepoRoot "services\mycobrain"
$StartScript = Join-Path $ScriptRoot "mycobrain-service.ps1"
$LogFile = Join-Path $RepoRoot "data\mycobrain_watcher.log"

$DataDir = Join-Path $RepoRoot "data"
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }

function Write-Log ($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
    Write-Host $line
}

function Restart-MycoBrain {
    Write-Log "Restarting MycoBrain service (file change detected)..."
    & $StartScript restart 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8003/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Log "MycoBrain restarted OK. Devices: $($r.devices_connected)"
    } catch {
        Write-Log "MycoBrain restart may have failed. Check: .\scripts\mycobrain-service.ps1 health" "WARN"
    }
}

if (-not (Test-Path $ServiceDir)) {
    Write-Log "ERROR: Service dir not found: $ServiceDir"
    exit 1
}
if (-not (Test-Path $StartScript)) {
    Write-Log "ERROR: mycobrain-service.ps1 not found: $StartScript"
    exit 1
}

Write-Log "=== MycoBrain Watcher started. Watching: $ServiceDir ==="
Write-Log "Restart service on any .py file change. Ctrl+C to stop."

# Start MycoBrain if not running
$conn = Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
if (-not $conn) {
    Write-Log "MycoBrain not running. Starting..."
    & $StartScript start 2>&1 | Out-Null
    Start-Sleep -Seconds 2
}

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $ServiceDir
$watcher.Filter = "*.py"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

$action = {
    $path = $Event.SourceEventArgs.FullPath
    $changeType = $Event.SourceEventArgs.ChangeType
    $Event.MessageData.Restart()
}

$handlers = Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $action -MessageData @{ Restart = { Restart-MycoBrain } }
Register-ObjectEvent -InputObject $watcher -EventName Created -Action $action -MessageData @{ Restart = { Restart-MycoBrain } } | Out-Null

try {
    while ($true) { Start-Sleep -Seconds 10 }
} finally {
    $watcher.EnableRaisingEvents = $false
    $handlers | Unregister-Event -ErrorAction SilentlyContinue
    Write-Log "MycoBrain Watcher stopped."
}
