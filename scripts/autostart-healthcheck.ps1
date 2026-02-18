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
    # ── PRIORITY 1: MycoBrain Service (24/7/365 ALWAYS-ON) ──
    @{
        Name        = "MycoBrain Service [CRITICAL]"
        PidFile     = Join-Path $DataDir "mycobrain_service.pid"
        SearchPattern = "mycobrain_service"
        StartScript = Join-Path $ProjectRoot "scripts\mycobrain-service.ps1"
        StartArgs   = "start"
        MaxMemoryMB = 200
        MaxCpuPct   = 10
        Port        = 8003
        HealthUrl   = "http://localhost:8003/health"
        Priority    = 1
    },
    @{
        Name        = "Notion Docs Watcher"
        PidFile     = Join-Path $DataDir "notion_watcher.pid"
        SearchPattern = "notion_docs_watcher"
        StartScript = Join-Path $ProjectRoot "scripts\notion-sync.ps1"
        StartArgs   = "watch-bg"
        MaxMemoryMB = 200
        MaxCpuPct   = 5
    },
    @{
        Name        = "Cursor System Sync"
        PidFile     = Join-Path $DataDir "cursor_sync.pid"
        SearchPattern = "sync_cursor_system"
        StartScript = "python"
        StartArgs   = (Join-Path $ProjectRoot "scripts\sync_cursor_system.py") + " --watch"
        MaxMemoryMB = 100
        MaxCpuPct   = 2
        Priority    = 3
    },
    @{
        Name        = "n8n Local (Docker)"
        ContainerName = "mycosoft-n8n"
        Type        = "docker"
        Port        = 5678
        HealthUrl   = "http://localhost:5678/healthz"
        StartScript = Join-Path $ProjectRoot "scripts\n8n-healthcheck.ps1"
        StartArgs   = "-StartLocal"
        MaxMemoryMB = 500
        MaxCpuPct   = 10
        Priority    = 2
    }
    # ── Dev Server Watchdog (Website port 3010) ──
    @{
        Name          = "Dev Server Watchdog [port 3010]"
        SearchPattern = "dev-server-watchdog"
        StartScript   = "powershell.exe"
        StartArgs     = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\scripts\dev-server-watchdog.ps1`""
        Port          = 3010
        HealthUrl     = "http://localhost:3010"
        MaxMemoryMB   = 50
        MaxCpuPct     = 1
        Priority      = 4
    }
    # ── Add new services below this line ──
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

    # Check Docker container first (for Type = "docker")
    if ($Service.Type -eq "docker" -and $Service.ContainerName) {
        try {
            $container = docker ps --filter "name=$($Service.ContainerName)" --format "{{.Names}}" 2>$null
            if ($container -eq $Service.ContainerName) {
                $status.Running = $true
                $status.PID = "docker"
                
                # Do HTTP health check if available
                if ($Service.HealthUrl) {
                    try {
                        $null = Invoke-WebRequest -Uri $Service.HealthUrl -TimeoutSec 3 -ErrorAction Stop
                    } catch {
                        $status.Healthy = $false
                        $status.Issue = "Health check failed: $($_.Exception.Message)"
                    }
                }
                return $status
            }
        } catch {
            # Docker not running or other error
        }
        return $status
    }

    # Check PID file first
    if ($Service.PidFile -and (Test-Path $Service.PidFile)) {
        $proc_id = Get-Content $Service.PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($proc_id -and $proc_id -match '^\d+$') {
            try {
                $proc = Get-Process -Id $proc_id -ErrorAction Stop
                if ($null -ne $proc -and $proc.HasExited -eq $false) {
                    $status.Running = $true
                    $status.PID = $proc_id
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
            } catch {
                # Process no longer exists
            }
        }
    }

    # Check by port if service has a Port defined
    if ($Service.Port) {
        $conn = Get-NetTCPConnection -LocalPort $Service.Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        if ($conn) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                $status.Running = $true
                $status.PID = $conn.OwningProcess
                $status.Memory = [math]::Round($proc.WorkingSet64 / 1MB, 1)
                $status.CPU = [math]::Round($proc.CPU, 1)
                
                # For services with HealthUrl, do HTTP health check
                if ($Service.HealthUrl) {
                    try {
                        $health = Invoke-RestMethod -Uri $Service.HealthUrl -TimeoutSec 3 -ErrorAction Stop
                        if ($health.status -ne "ok") {
                            $status.Healthy = $false
                            $status.Issue = "Health check returned: $($health.status)"
                        }
                    } catch {
                        $status.Healthy = $false
                        $status.Issue = "Health check failed: $($_.Exception.Message)"
                    }
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

    Write-Host "  Starting $($Service.Name)..." -ForegroundColor Yellow

    # Docker container service
    if ($Service.Type -eq "docker" -and $Service.ContainerName) {
        # Check if Docker is running
        try {
            $dockerInfo = docker info 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Docker Desktop is not running. Start Docker first." -ForegroundColor Red
                return
            }
        } catch {
            Write-Host "  Docker Desktop is not running. Start Docker first." -ForegroundColor Red
            return
        }

        # Check if container exists but is stopped
        $exists = docker ps -a --filter "name=$($Service.ContainerName)" --format "{{.Names}}" 2>$null
        if ($exists -eq $Service.ContainerName) {
            docker start $Service.ContainerName 2>$null
        } elseif ($Service.StartScript -and (Test-Path $Service.StartScript)) {
            # Use start script to create container
            & $Service.StartScript $Service.StartArgs
        } else {
            Write-Host "  Container does not exist. Create it first." -ForegroundColor Red
            return
        }

        Start-Sleep -Seconds 3
        $check = Get-ServiceStatus $Service
        if ($check.Running) {
            Write-Host "  Started (container: $($Service.ContainerName))" -ForegroundColor Green
        } else {
            Write-Host "  FAILED to start" -ForegroundColor Red
        }
        return
    }

    # Regular process service
    if ($Service.StartScript -and (Test-Path $Service.StartScript)) {
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
    elseif ($Service.StartScript -eq "python") {
        # Special case for python scripts
        Start-Process -FilePath "python" -ArgumentList $Service.StartArgs -WindowStyle Hidden
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
        Write-Host "  Stopping $($Service.Name)..." -ForegroundColor Yellow

        # Docker container service
        if ($Service.Type -eq "docker" -and $Service.ContainerName) {
            docker stop $Service.ContainerName 2>$null
            Write-Host "  Stopped (container: $($Service.ContainerName))" -ForegroundColor Green
            return
        }

        # Regular process
        if ($status.PID -and $status.PID -ne "docker") {
            Stop-Process -Id $status.PID -Force -ErrorAction SilentlyContinue
        }
        if ($Service.PidFile -and (Test-Path $Service.PidFile)) {
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

# ── Docker Health Check (periodic) ────────────────────────────────────────────

Write-Host ""
Write-Host "─── Docker Health ───" -ForegroundColor Cyan

$dockerHealthScript = Join-Path $ProjectRoot "scripts\docker-healthcheck.ps1"
if (Test-Path $dockerHealthScript) {
    try {
        # Check if Docker is running
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            # Get quick health metrics
            $containerCount = (docker ps -aq 2>$null | Measure-Object).Count
            $runningCount = (docker ps -q 2>$null | Measure-Object).Count
            $stoppedCount = $containerCount - $runningCount
            
            # Check vmmem
            $vmmem = Get-Process vmmem -ErrorAction SilentlyContinue
            $vmmemMB = if ($vmmem) { [math]::Round($vmmem.WorkingSet64 / 1MB) } else { 0 }
            
            Write-Host "[OK]     Docker Desktop running (containers: $runningCount running, $stoppedCount stopped)"
            if ($vmmemMB -gt 0) {
                $color = if ($vmmemMB -gt 4096) { "Yellow" } else { "Green" }
                Write-Host "         vmmem: ${vmmemMB}MB" -ForegroundColor $color
            }
            
            # Check for cleanup needs
            $needsCleanup = $false
            $danglingImages = docker images -f "dangling=true" -q 2>$null
            $danglingCount = if ($danglingImages) { ($danglingImages | Measure-Object).Count } else { 0 }
            
            if ($stoppedCount -gt 0 -or $danglingCount -gt 0 -or $vmmemMB -gt 4096) {
                $needsCleanup = $true
                if ($stoppedCount -gt 0) {
                    Write-Host "[WARN]   $stoppedCount stopped container(s) can be cleaned up" -ForegroundColor Yellow
                }
                if ($danglingCount -gt 0) {
                    Write-Host "[WARN]   $danglingCount dangling image(s) can be cleaned up" -ForegroundColor Yellow
                }
                if ($vmmemMB -gt 4096) {
                    Write-Host "[WARN]   vmmem high (${vmmemMB}MB > 4096MB limit)" -ForegroundColor Yellow
                }
            }
            
            if ($needsCleanup) {
                Write-Host ""
                Write-Host "         Run: .\scripts\docker-healthcheck.ps1 -Cleanup" -ForegroundColor Gray
            }
        } else {
            Write-Host "[DOWN]   Docker Desktop not running" -ForegroundColor Red
            Write-Host "         Run: .\scripts\docker-healthcheck.ps1 -StartDocker" -ForegroundColor Gray
        }
    } catch {
        Write-Host "[WARN]   Could not check Docker: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[SKIP]   docker-healthcheck.ps1 not found" -ForegroundColor Gray
}

Write-Host ""
