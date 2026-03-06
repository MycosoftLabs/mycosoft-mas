# ensure-cowork-vm-watchdog.ps1
# Silent watchdog: checks CoworkVMService, starts if down, logs actions.
# Run by scheduled task every 2 min + at startup. MAR04 2026
# CRITICAL: Claude Cowork automates COO, Secretary, HR, assignments - must stay up.

$logDir = "$env:LOCALAPPDATA\Mycosoft\cowork-watchdog"
$logFile = "$logDir\watchdog.log"
$maxLogLines = 500

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-WatchdogLog {
    param([string]$msg, [string]$level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$level] $msg"
    Add-Content -Path $logFile -Value $line -ErrorAction SilentlyContinue
    # Trim log
    if (Test-Path $logFile) {
        $lines = Get-Content $logFile -ErrorAction SilentlyContinue
        if ($lines.Count -gt $maxLogLines) {
            $lines | Select-Object -Last $maxLogLines | Set-Content $logFile -Force
        }
    }
}

try {
    $svc = Get-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-WatchdogLog "CoworkVMService not found - Claude Desktop may not be installed" "WARN"
        exit 0
    }

    if ($svc.Status -ne "Running") {
        Write-WatchdogLog "CoworkVMService is $($svc.Status) - attempting start" "WARN"
        try {
            Start-Service -Name "CoworkVMService" -ErrorAction Stop
            Set-Service -Name "CoworkVMService" -StartupType Automatic -ErrorAction SilentlyContinue
            Write-WatchdogLog "CoworkVMService started successfully" "INFO"
        } catch {
            Write-WatchdogLog "Failed to start: $($_.Exception.Message)" "ERROR"
        }
    }
} catch {
    Write-WatchdogLog "Watchdog error: $($_.Exception.Message)" "ERROR"
}
