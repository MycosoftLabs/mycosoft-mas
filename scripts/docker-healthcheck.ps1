# Docker Healthcheck and Cleanup (Feb 12, 2026)
# Manages Docker Desktop resources, cleans unused containers/images, reports to MAS.
#
# Usage:
#   .\scripts\docker-healthcheck.ps1              # Quick health check
#   .\scripts\docker-healthcheck.ps1 -Quick       # Same as above
#   .\scripts\docker-healthcheck.ps1 -Cleanup     # Full cleanup of unused resources
#   .\scripts\docker-healthcheck.ps1 -StartDocker # Start Docker Desktop if not running
#   .\scripts\docker-healthcheck.ps1 -Json        # Output as JSON (for MAS integration)
#   .\scripts\docker-healthcheck.ps1 -ReportToMAS # Send health report to MAS API

param(
    [switch]$Quick,
    [switch]$Cleanup,
    [switch]$StartDocker,
    [switch]$Json,
    [switch]$ReportToMAS,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

# ── Configuration ─────────────────────────────────────────────────────────────

$MAS_API_URL = "http://192.168.0.188:8001"
$DOCKER_DESKTOP_PATH = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Required/known local containers (these are expected to run)
# Prefixes to recognize as valid Mycosoft containers
$KnownContainerPrefixes = @(
    "mycosoft-",
    "mas-",
    "myca-"
)

# Critical containers that MUST be running for dev to work
$RequiredContainers = @(
    @{ Name = "mycosoft-n8n"; Image = "n8nio/n8n"; Port = 5678 }
    @{ Name = "mycosoft-mas-n8n-1"; Image = "n8nio/n8n"; Port = 5678 }
)

# Resource limits
$Limits = @{
    MaxContainers = 10
    MaxImages = 20
    MaxBuildCacheGB = 5
    MaxVmmemMB = 4096
    MaxDiskUsageGB = 20
}

# ── Helper Functions ──────────────────────────────────────────────────────────

function Test-DockerRunning {
    try {
        $info = docker info 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Start-DockerDesktop {
    if (Test-DockerRunning) {
        if (-not $Json) { Write-Host "[OK]   Docker Desktop is running" -ForegroundColor Green }
        return $true
    }

    if (-not $Json) { Write-Host "[...] Starting Docker Desktop..." -ForegroundColor Yellow }

    if (Test-Path $DOCKER_DESKTOP_PATH) {
        Start-Process $DOCKER_DESKTOP_PATH
        
        # Wait for Docker to be ready (max 60 seconds)
        $maxWait = 60
        $waited = 0
        while (-not (Test-DockerRunning) -and $waited -lt $maxWait) {
            Start-Sleep -Seconds 2
            $waited += 2
            if (-not $Json -and $Verbose) { Write-Host "       Waiting... ($waited s)" -ForegroundColor Gray }
        }
        
        if (Test-DockerRunning) {
            if (-not $Json) { Write-Host "[OK]   Docker Desktop started" -ForegroundColor Green }
            return $true
        } else {
            if (-not $Json) { Write-Host "[FAIL] Docker Desktop did not start in time" -ForegroundColor Red }
            return $false
        }
    } else {
        if (-not $Json) { Write-Host "[FAIL] Docker Desktop not found at $DOCKER_DESKTOP_PATH" -ForegroundColor Red }
        return $false
    }
}

function Get-DockerHealth {
    $health = @{
        Timestamp = Get-Date -Format "o"
        Hostname = $env:COMPUTERNAME
        DockerRunning = $false
        RequiredContainersOk = $false
        Containers = @()
        Images = @()
        DiskUsage = @{}
        VmmemMB = 0
        Issues = @()
        NeedsCleanup = $false
    }

    # Check if Docker is running
    $health.DockerRunning = Test-DockerRunning
    if (-not $health.DockerRunning) {
        $health.Issues += "Docker Desktop is not running"
        return $health
    }

    # Get container info
    try {
        $containers = docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}" 2>$null
        foreach ($line in $containers) {
            if ($line) {
                $parts = $line -split '\|'
                $health.Containers += @{
                    Name = $parts[0]
                    Image = $parts[1]
                    Status = $parts[2]
                    Ports = $parts[3]
                    Running = $parts[2] -like "Up*"
                }
            }
        }
    } catch { }

    # Check required containers
    $requiredOk = $true
    foreach ($req in $RequiredContainers) {
        $found = $health.Containers | Where-Object { $_.Name -eq $req.Name -and $_.Running }
        if (-not $found) {
            $requiredOk = $false
            $health.Issues += "Required container '$($req.Name)' is not running"
        }
    }
    $health.RequiredContainersOk = $requiredOk

    # Get image info
    try {
        $images = docker images --format "{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}" 2>$null
        foreach ($line in $images) {
            if ($line) {
                $parts = $line -split '\|'
                $health.Images += @{
                    Name = $parts[0]
                    Size = $parts[1]
                    Age = $parts[2]
                }
            }
        }
    } catch { }

    # Get disk usage
    try {
        $diskUsage = docker system df --format "{{.Type}}|{{.Size}}|{{.Reclaimable}}" 2>$null
        foreach ($line in $diskUsage) {
            if ($line) {
                $parts = $line -split '\|'
                $health.DiskUsage[$parts[0]] = @{
                    Size = $parts[1]
                    Reclaimable = $parts[2]
                }
            }
        }
    } catch { }

    # Check vmmem memory
    try {
        $vmmem = Get-Process vmmem -ErrorAction SilentlyContinue
        if ($vmmem) {
            $health.VmmemMB = [math]::Round($vmmem.WorkingSet64 / 1MB)
            if ($health.VmmemMB -gt $Limits.MaxVmmemMB) {
                $health.Issues += "vmmem using $($health.VmmemMB)MB (limit: $($Limits.MaxVmmemMB)MB)"
                $health.NeedsCleanup = $true
            }
        }
    } catch { }

    # Check container count
    $stoppedContainers = ($health.Containers | Where-Object { -not $_.Running }).Count
    if ($stoppedContainers -gt 0) {
        $health.Issues += "$stoppedContainers stopped container(s) can be removed"
        $health.NeedsCleanup = $true
    }

    # Check for unknown running containers (containers not matching known prefixes)
    $runningContainers = $health.Containers | Where-Object { $_.Running }
    foreach ($c in $runningContainers) {
        $isKnown = $false
        foreach ($prefix in $KnownContainerPrefixes) {
            if ($c.Name -like "$prefix*") {
                $isKnown = $true
                break
            }
        }
        if (-not $isKnown) {
            $health.Issues += "Unknown container '$($c.Name)' is running"
        }
    }

    # Check image count
    $danglingImages = docker images -f "dangling=true" -q 2>$null
    if ($danglingImages) {
        $danglingCount = ($danglingImages | Measure-Object).Count
        if ($danglingCount -gt 0) {
            $health.Issues += "$danglingCount dangling image(s) can be removed"
            $health.NeedsCleanup = $true
        }
    }

    return $health
}

function Invoke-DockerCleanup {
    if (-not $Json) {
        Write-Host ""
        Write-Host "─── DOCKER CLEANUP ───" -ForegroundColor Yellow
        Write-Host ""
    }

    $cleaned = @{
        Containers = 0
        Images = 0
        Volumes = 0
        BuildCache = $false
    }

    # Remove stopped containers
    if (-not $Json) { Write-Host "[...] Removing stopped containers..." -ForegroundColor Yellow }
    try {
        $result = docker container prune -f 2>&1
        if ($result -match "Total reclaimed space: (.+)") {
            $cleaned.Containers = $Matches[1]
            if (-not $Json) { Write-Host "[OK]   Reclaimed: $($Matches[1])" -ForegroundColor Green }
        } else {
            if (-not $Json) { Write-Host "[OK]   No stopped containers to remove" -ForegroundColor Green }
        }
    } catch {
        if (-not $Json) { Write-Host "[WARN] Failed to prune containers" -ForegroundColor Yellow }
    }

    # Remove dangling images
    if (-not $Json) { Write-Host "[...] Removing dangling images..." -ForegroundColor Yellow }
    try {
        $result = docker image prune -f 2>&1
        if ($result -match "Total reclaimed space: (.+)") {
            $cleaned.Images = $Matches[1]
            if (-not $Json) { Write-Host "[OK]   Reclaimed: $($Matches[1])" -ForegroundColor Green }
        } else {
            if (-not $Json) { Write-Host "[OK]   No dangling images to remove" -ForegroundColor Green }
        }
    } catch {
        if (-not $Json) { Write-Host "[WARN] Failed to prune images" -ForegroundColor Yellow }
    }

    # Remove unused volumes
    if (-not $Json) { Write-Host "[...] Removing unused volumes..." -ForegroundColor Yellow }
    try {
        $result = docker volume prune -f 2>&1
        if ($result -match "Total reclaimed space: (.+)") {
            $cleaned.Volumes = $Matches[1]
            if (-not $Json) { Write-Host "[OK]   Reclaimed: $($Matches[1])" -ForegroundColor Green }
        } else {
            if (-not $Json) { Write-Host "[OK]   No unused volumes to remove" -ForegroundColor Green }
        }
    } catch {
        if (-not $Json) { Write-Host "[WARN] Failed to prune volumes" -ForegroundColor Yellow }
    }

    # Check build cache size and prune if large
    try {
        $buildCache = docker system df --format "{{.Type}}|{{.Size}}" 2>$null | Where-Object { $_ -like "Build*" }
        if ($buildCache) {
            $size = ($buildCache -split '\|')[1]
            if ($size -match "(\d+\.?\d*)GB" -and [double]$Matches[1] -gt $Limits.MaxBuildCacheGB) {
                if (-not $Json) { Write-Host "[...] Build cache is $size, pruning..." -ForegroundColor Yellow }
                docker builder prune -f 2>$null
                $cleaned.BuildCache = $true
                if (-not $Json) { Write-Host "[OK]   Build cache pruned" -ForegroundColor Green }
            }
        }
    } catch { }

    if (-not $Json) {
        Write-Host ""
        Write-Host "[OK]   Cleanup complete" -ForegroundColor Green
        Write-Host ""
    }

    return $cleaned
}

function Send-HealthToMAS {
    param($Health)

    if (-not $Json) { Write-Host "[...] Sending health report to MAS..." -ForegroundColor Yellow }

    try {
        $response = Invoke-RestMethod -Uri "$MAS_API_URL/api/infrastructure/docker-health" `
            -Method POST `
            -Body ($Health | ConvertTo-Json -Depth 5) `
            -ContentType "application/json" `
            -TimeoutSec 10 `
            -ErrorAction Stop

        if (-not $Json) { Write-Host "[OK]   Report sent to MAS" -ForegroundColor Green }
        return $true
    } catch {
        if (-not $Json) { Write-Host "[WARN] Failed to send to MAS: $($_.Exception.Message)" -ForegroundColor Yellow }
        return $false
    }
}

function Show-HealthReport {
    param($Health)

    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host "  DOCKER DESKTOP HEALTH CHECK"
    Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""

    # Docker status
    if ($Health.DockerRunning) {
        Write-Host "[OK]   Docker Desktop is running" -ForegroundColor Green
    } else {
        Write-Host "[DOWN] Docker Desktop is not running" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Run: .\scripts\docker-healthcheck.ps1 -StartDocker" -ForegroundColor Gray
        Write-Host ""
        return
    }

    # Required containers
    Write-Host ""
    Write-Host "─── Required Containers ───" -ForegroundColor Cyan
    foreach ($req in $RequiredContainers) {
        $found = $Health.Containers | Where-Object { $_.Name -eq $req.Name }
        if ($found -and $found.Running) {
            Write-Host "[OK]   $($req.Name) (port $($req.Port))" -ForegroundColor Green
        } elseif ($found) {
            Write-Host "[STOP] $($req.Name) - stopped" -ForegroundColor Yellow
        } else {
            Write-Host "[MISS] $($req.Name) - not found" -ForegroundColor Red
        }
    }

    # Other running containers (show by category)
    $otherContainers = $Health.Containers | Where-Object { $_.Name -notin ($RequiredContainers | ForEach-Object { $_.Name }) }
    $runningOther = $otherContainers | Where-Object { $_.Running }
    $stoppedOther = $otherContainers | Where-Object { -not $_.Running }
    
    if ($runningOther) {
        Write-Host ""
        Write-Host "─── Running Containers ($($runningOther.Count)) ───" -ForegroundColor Cyan
        foreach ($c in $runningOther) {
            # Check if it's a known Mycosoft container
            $isKnown = $false
            foreach ($prefix in $KnownContainerPrefixes) {
                if ($c.Name -like "$prefix*") {
                    $isKnown = $true
                    break
                }
            }
            if ($isKnown) {
                Write-Host "[OK]   $($c.Name)" -ForegroundColor Green
            } else {
                Write-Host "[???]  $($c.Name) - UNKNOWN" -ForegroundColor Yellow
            }
        }
    }
    
    if ($stoppedOther) {
        Write-Host ""
        Write-Host "─── Stopped Containers ($($stoppedOther.Count)) ───" -ForegroundColor Gray
        foreach ($c in $stoppedOther) {
            Write-Host "[STOP] $($c.Name) (can be removed)" -ForegroundColor Gray
        }
    }

    # Resource usage
    Write-Host ""
    Write-Host "─── Resources ───" -ForegroundColor Cyan
    Write-Host "  Containers: $($Health.Containers.Count) (limit: $($Limits.MaxContainers))"
    Write-Host "  Images:     $($Health.Images.Count) (limit: $($Limits.MaxImages))"
    Write-Host "  vmmem:      $($Health.VmmemMB)MB (limit: $($Limits.MaxVmmemMB)MB)"

    if ($Health.DiskUsage.Count -gt 0) {
        Write-Host ""
        Write-Host "─── Disk Usage ───" -ForegroundColor Cyan
        foreach ($key in $Health.DiskUsage.Keys) {
            $usage = $Health.DiskUsage[$key]
            Write-Host "  ${key}: $($usage.Size) (reclaimable: $($usage.Reclaimable))"
        }
    }

    # Issues
    if ($Health.Issues.Count -gt 0) {
        Write-Host ""
        Write-Host "─── Issues ───" -ForegroundColor Yellow
        foreach ($issue in $Health.Issues) {
            Write-Host "  - $issue" -ForegroundColor Yellow
        }
    }

    # Summary
    Write-Host ""
    if ($Health.Issues.Count -eq 0) {
        Write-Host "[OK]   Docker is healthy" -ForegroundColor Green
    } elseif ($Health.NeedsCleanup) {
        Write-Host "[WARN] Docker needs cleanup" -ForegroundColor Yellow
        Write-Host "       Run: .\scripts\docker-healthcheck.ps1 -Cleanup" -ForegroundColor Gray
    } else {
        Write-Host "[WARN] Some issues found" -ForegroundColor Yellow
    }
    Write-Host ""
}

# ── Main ──────────────────────────────────────────────────────────────────────

# Start Docker if requested
if ($StartDocker) {
    $started = Start-DockerDesktop
    if (-not $started) {
        exit 1
    }
}

# Check if Docker is running
if (-not (Test-DockerRunning)) {
    if ($Json) {
        @{ DockerRunning = $false; Error = "Docker Desktop is not running" } | ConvertTo-Json
    } else {
        Write-Host ""
        Write-Host "[DOWN] Docker Desktop is not running" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Run: .\scripts\docker-healthcheck.ps1 -StartDocker" -ForegroundColor Gray
        Write-Host ""
    }
    exit 1
}

# Get health info
$health = Get-DockerHealth

# Cleanup if requested
if ($Cleanup) {
    $cleanupResult = Invoke-DockerCleanup
    $health = Get-DockerHealth  # Refresh health after cleanup
}

# Report to MAS if requested
if ($ReportToMAS) {
    Send-HealthToMAS $health
}

# Output
if ($Json) {
    $health | ConvertTo-Json -Depth 5
} else {
    Show-HealthReport $health
}
