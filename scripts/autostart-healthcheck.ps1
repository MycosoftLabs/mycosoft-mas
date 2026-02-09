# Autostart Services Health Check (Feb 08, 2026)
# Checks, starts, and monitors all registered autostart background services.
#
# Usage:
#   .\scripts\autostart-healthcheck.ps1                  # Check status of all services
#   .\scripts\autostart-healthcheck.ps1 -StartMissing    # Start any services that aren't running
#   .\scripts\autostart-healthcheck.ps1 -StopAll         # Stop all autostart services
#   .\scripts\autostart-healthcheck.ps1 -Verbose         # Detailed output

param(
    [switch]$StartMissing,
    [switch]$StopAll,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DataDir = Join-Path $ProjectRoot "data"

# ── Registered Autostart Services ────────────────────────────────────────────
# Add new services here. Each entry needs:
#   Name        - Display name
#   PidFile     - Path to PID file (relative to project root data/)
#   CheckCmd    - How to find the running process
#   StartCmd    - How to start it
#   ProcessName - Process name pattern to search for

$Services = @(
    @{
        Name        = "Notion Docs Watcher"
        PidFile     = Join-Path $DataDir "notion_watcher.pid"
        SearchPattern = "notion_docs_watcher"
        StartScript = Join-Path $ProjectRoot "scripts\notion-sync.ps1"
        StartArgs   = "watch-bg"
        MaxMemoryMB = 200
        MaxCpuPct   = 5
    }
    # ── Add new services below this line ──
    # @{
    #     Name        = "Service Name"
    #     PidFile     = Join-Path $DataDir "service.pid"
    #     SearchPattern = "script_name"
    #     StartScript = Join-Path $ProjectRoot "scripts\start-script.ps1"
    #     StartArgs   = ""
    #     MaxMemoryMB = 200
    #     MaxCpuPct   = 5
    # }
)

# ── Functions ────────────────────────────────────────────────────────────────

function Get-ServiceStatus {
    param($Service)

    $status = @{
        Name    = $Service.Name
        Running = $false
        PID     = $null
        Memory  = $null
        CPU     = $null
        Healthy = $true
        Issue   = ""
    }

    # Check PID file first
    if (Test-Path $Service.PidFile) {
        $pid = Get-Content $Service.PidFile -ErrorAction SilentlyContinue
        if ($pid) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                $status.Running = $true
                $status.PID = $pid
                $status.Memory = [math]::Round($proc.WorkingSet64 / 1MB, 1)
                # CPU percentage is approximate
                $status.CPU = [math]::Round($proc.CPU, 1)

                # Check resource limits
                if ($status.Memory -gt $Service.MaxMemoryMB) {
                    $status.Healthy = $false
                    $status.Issue = "HIGH MEMORY: $($status.Memory)MB > $($Service.MaxMemoryMB)MB limit"
                }
                return $status
            }
        }
    }

    # Fallback: search by process pattern
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*$($Service.SearchPattern)*" }

    if ($procs -and $procs.Count -gt 0) {
        $proc = $procs[0]
        $status.Running = $true
        $status.PID = $proc.Id
        $status.Memory = [math]::Round($proc.WorkingSet64 / 1MB, 1)
        $status.CPU = [math]::Round($proc.CPU, 1)
    }

    return $status
}

function Start-Service {
    param($Service)

    if (Test-Path $Service.StartScript) {
        Write-Host "  Starting $($Service.Name)..." -ForegroundColor Yellow
        & $Service.StartScript $Service.StartArgs
        Start-Sleep -Seconds 2
        $check = Get-ServiceStatus $Service
        if ($check.Running) {
            Write-Host "  Started (PID: $($check.PID))" -ForegroundColor Green
        }
        else {
            Write-Host "  FAILED to start" -ForegroundColor Red
        }
    }
    else {
        Write-Host "  Start script not found: $($Service.StartScript)" -ForegroundColor Red
    }
}

function Stop-Service {
    param($Service)

    $status = Get-ServiceStatus $Service
    if ($status.Running) {
        Write-Host "  Stopping $($Service.Name) (PID: $($status.PID))..." -ForegroundColor Yellow
        Stop-Process -Id $status.PID -Force -ErrorAction SilentlyContinue
        if (Test-Path $Service.PidFile) {
            Remove-Item $Service.PidFile -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  Stopped" -ForegroundColor Green
    }
    else {
        Write-Host "  $($Service.Name) was not running" -ForegroundColor Gray
    }
}

# ── Main ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT AUTOSTART SERVICES HEALTH CHECK"
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

if ($StopAll) {
    Write-Host "Stopping all autostart services..." -ForegroundColor Yellow
    foreach ($svc in $Services) {
        Stop-Service $svc
    }
    Write-Host ""
    Write-Host "All services stopped." -ForegroundColor Green
    exit 0
}

$allHealthy = $true
$missingSvcs = @()

foreach ($svc in $Services) {
    $status = Get-ServiceStatus $svc

    if ($status.Running) {
        if ($status.Healthy) {
            Write-Host "[OK]     $($svc.Name)" -ForegroundColor Green
        }
        else {
            Write-Host "[WARN]   $($svc.Name) - $($status.Issue)" -ForegroundColor Yellow
            $allHealthy = $false
        }
        if ($Verbose) {
            Write-Host "         PID: $($status.PID) | Memory: $($status.Memory)MB | CPU: $($status.CPU)s"
        }
    }
    else {
        Write-Host "[DOWN]   $($svc.Name)" -ForegroundColor Red
        $allHealthy = $false
        $missingSvcs += $svc
    }
}

Write-Host ""

if ($StartMissing -and $missingSvcs.Count -gt 0) {
    Write-Host "Starting missing services..." -ForegroundColor Yellow
    foreach ($svc in $missingSvcs) {
        Start-Service $svc
    }
    Write-Host ""
}
elseif ($missingSvcs.Count -gt 0 -and -not $StartMissing) {
    Write-Host "$($missingSvcs.Count) service(s) not running." -ForegroundColor Yellow
    Write-Host "Run with -StartMissing to start them." -ForegroundColor Gray
}

if ($allHealthy -and $missingSvcs.Count -eq 0) {
    Write-Host "All autostart services are healthy." -ForegroundColor Green
}

Write-Host ""
