# ensure-cto-vm-watchdog.ps1
# Silent watchdog: checks OpenClaw, Cursor, workspace; restarts OpenClaw if needed; sends enriched heartbeat.
# Run by scheduled task every 2 min + at startup. MAR08 2026
# CRITICAL: CTO VM 194 autonomy — Forge/Cursor must stay healthy.

$logDir = "$env:LOCALAPPDATA\Mycosoft\cto-watchdog"
$logFile = "$logDir\watchdog.log"
$maxLogLines = 500

# Script roots — assume run from MAS repo scripts/
$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$masRepo = Split-Path $scriptDir -Parent
$infraCsuite = Join-Path $masRepo "infra\csuite"
$forgeBridge = Join-Path $infraCsuite "forge_bridge_run.ps1"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-WatchdogLog {
    param([string]$msg, [string]$level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$level] $msg"
    Add-Content -Path $logFile -Value $line -ErrorAction SilentlyContinue
    if (Test-Path $logFile) {
        $lines = Get-Content $logFile -ErrorAction SilentlyContinue
        if ($lines -and $lines.Count -gt $maxLogLines) {
            $lines | Select-Object -Last $maxLogLines | Set-Content $logFile -Force
        }
    }
}

try {
    # --- OpenClaw check ---
    $openclawProc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "openclaw" }
    if (-not $openclawProc) {
        # OpenClaw not running — try to start (optional; may need user context)
        $openclawPath = Get-Command openclaw -ErrorAction SilentlyContinue
        if ($openclawPath) {
            Write-WatchdogLog "OpenClaw not running — attempting start" "WARN"
            try {
                Start-Process -FilePath "openclaw" -ArgumentList "daemon" -WindowStyle Hidden -ErrorAction Stop
                Start-Sleep -Seconds 3
                Write-WatchdogLog "OpenClaw start attempted" "INFO"
            } catch {
                Write-WatchdogLog "OpenClaw start failed: $($_.Exception.Message)" "WARN"
            }
        } else {
            Write-WatchdogLog "OpenClaw binary not found" "WARN"
        }
    }

    # --- Send enriched heartbeat via forge_bridge_run ---
    if (Test-Path $forgeBridge) {
        try {
            & $forgeBridge -Silent
        } catch {
            Write-WatchdogLog "Forge bridge run failed: $_" "WARN"
        }
    } else {
        Write-WatchdogLog "forge_bridge_run.ps1 not found at $forgeBridge" "WARN"
    }
} catch {
    Write-WatchdogLog "CTO watchdog error: $($_.Exception.Message)" "ERROR"
}
