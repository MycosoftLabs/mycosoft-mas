# Check All Environments Health (Feb 12, 2026)
# Comprehensive health check for local dev environment and all VMs.
#
# Usage:
#   .\scripts\check-all-environments.ps1           # Check all environments
#   .\scripts\check-all-environments.ps1 -Local    # Check only local services
#   .\scripts\check-all-environments.ps1 -VMs      # Check only VM services
#   .\scripts\check-all-environments.ps1 -Verbose  # Include detailed output

param(
    [switch]$Local,
    [switch]$VMs,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# VM Configuration
$VM_SANDBOX = "192.168.0.187"
$VM_MAS     = "192.168.0.188"
$VM_MINDEX  = "192.168.0.189"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT ENVIRONMENT HEALTH CHECK"
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$allHealthy = $true
$summary = @{
    LocalOk = 0
    LocalDown = 0
    VMOk = 0
    VMDown = 0
}

# ── Helper Functions ──────────────────────────────────────────────────────────

function Test-HttpEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSec = 5
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK]   $Name" -ForegroundColor Green
            if ($Verbose) {
                Write-Host "       URL: $Url" -ForegroundColor Gray
            }
            return $true
        } else {
            Write-Host "[WARN] $Name - Status: $($response.StatusCode)" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "[DOWN] $Name" -ForegroundColor Red
        if ($Verbose) {
            Write-Host "       URL: $Url" -ForegroundColor Gray
            Write-Host "       Error: $($_.Exception.Message)" -ForegroundColor Gray
        }
        return $false
    }
}

function Test-TcpPort {
    param(
        [string]$Name,
        [string]$Host,
        [int]$Port,
        [int]$TimeoutMs = 3000
    )
    
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect($Host, $Port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        
        if ($wait -and $tcp.Connected) {
            $tcp.Close()
            Write-Host "[OK]   $Name" -ForegroundColor Green
            if ($Verbose) {
                Write-Host "       ${Host}:${Port}" -ForegroundColor Gray
            }
            return $true
        } else {
            $tcp.Close()
            Write-Host "[DOWN] $Name" -ForegroundColor Red
            if ($Verbose) {
                Write-Host "       ${Host}:${Port} - Connection timeout" -ForegroundColor Gray
            }
            return $false
        }
    } catch {
        Write-Host "[DOWN] $Name" -ForegroundColor Red
        if ($Verbose) {
            Write-Host "       ${Host}:${Port} - $($_.Exception.Message)" -ForegroundColor Gray
        }
        return $false
    }
}

function Test-DockerRunning {
    try {
        $dockerInfo = docker info 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-DockerContainer {
    param(
        [string]$Name,
        [string]$ContainerName
    )
    
    try {
        $container = docker ps --filter "name=$ContainerName" --format "{{.Names}}" 2>$null
        if ($container -eq $ContainerName) {
            Write-Host "[OK]   $Name" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[DOWN] $Name" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "[DOWN] $Name" -ForegroundColor Red
        return $false
    }
}

function Test-LocalProcess {
    param(
        [string]$Name,
        [string]$Pattern
    )
    
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*$Pattern*" }
        
        if ($procs) {
            Write-Host "[OK]   $Name" -ForegroundColor Green
            if ($Verbose) {
                Write-Host "       PID: $($procs.ProcessId)" -ForegroundColor Gray
            }
            return $true
        } else {
            Write-Host "[DOWN] $Name" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "[DOWN] $Name" -ForegroundColor Red
        return $false
    }
}

function Test-LocalPort {
    param(
        [string]$Name,
        [int]$Port
    )
    
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        if ($conn) {
            Write-Host "[OK]   $Name" -ForegroundColor Green
            if ($Verbose) {
                Write-Host "       Port: $Port (PID: $($conn.OwningProcess))" -ForegroundColor Gray
            }
            return $true
        } else {
            Write-Host "[DOWN] $Name" -ForegroundColor Red
            if ($Verbose) {
                Write-Host "       Port $Port not listening" -ForegroundColor Gray
            }
            return $false
        }
    } catch {
        Write-Host "[DOWN] $Name" -ForegroundColor Red
        return $false
    }
}

# ── Local Environment Check ───────────────────────────────────────────────────

if (-not $VMs) {
    Write-Host "─── LOCAL DEVELOPMENT ───" -ForegroundColor Cyan
    Write-Host ""
    
    # Docker Desktop
    if (Test-DockerRunning) {
        Write-Host "[OK]   Docker Desktop" -ForegroundColor Green
        $summary.LocalOk++
        
        # n8n container
        if (Test-DockerContainer -Name "n8n Local (port 5678)" -ContainerName "mycosoft-n8n") {
            $summary.LocalOk++
        } else {
            $summary.LocalDown++
            $allHealthy = $false
        }
    } else {
        Write-Host "[DOWN] Docker Desktop" -ForegroundColor Red
        Write-Host "[SKIP] n8n Local - Docker not running" -ForegroundColor Yellow
        $summary.LocalDown++
        $allHealthy = $false
    }
    
    # MycoBrain Service
    if (Test-LocalPort -Name "MycoBrain Service (port 8003)" -Port 8003) {
        $summary.LocalOk++
    } else {
        $summary.LocalDown++
        $allHealthy = $false
    }
    
    # Cursor Sync Watcher
    if (Test-LocalProcess -Name "Cursor Sync Watcher" -Pattern "sync_cursor_system") {
        $summary.LocalOk++
    } else {
        $summary.LocalDown++
        $allHealthy = $false
    }
    
    # Notion Docs Watcher
    if (Test-LocalProcess -Name "Notion Docs Watcher" -Pattern "notion_docs_watcher") {
        $summary.LocalOk++
    } else {
        $summary.LocalDown++
        $allHealthy = $false
    }
    
    # Website Dev Server (optional)
    $devServer = Get-NetTCPConnection -LocalPort 3010 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($devServer) {
        Write-Host "[OK]   Website Dev Server (port 3010)" -ForegroundColor Green
        $summary.LocalOk++
    } else {
        Write-Host "[INFO] Website Dev Server (port 3010) - Not running (optional)" -ForegroundColor Gray
    }
    
    Write-Host ""
}

# ── VM Environment Check ──────────────────────────────────────────────────────

if (-not $Local) {
    Write-Host "─── VM 187 - SANDBOX ($VM_SANDBOX) ───" -ForegroundColor Cyan
    Write-Host ""
    
    # Website
    if (Test-HttpEndpoint -Name "Website (port 3000)" -Url "http://${VM_SANDBOX}:3000") {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    # Mycorrhizae API
    if (Test-TcpPort -Name "Mycorrhizae API (port 8002)" -Host $VM_SANDBOX -Port 8002) {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    Write-Host ""
    Write-Host "─── VM 188 - MAS ($VM_MAS) ───" -ForegroundColor Cyan
    Write-Host ""
    
    # MAS Orchestrator
    if (Test-HttpEndpoint -Name "MAS Orchestrator (port 8001)" -Url "http://${VM_MAS}:8001/health") {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    # n8n Production
    if (Test-TcpPort -Name "n8n Production (port 5678)" -Host $VM_MAS -Port 5678) {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    # Ollama
    if (Test-TcpPort -Name "Ollama LLM (port 11434)" -Host $VM_MAS -Port 11434) {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    # Prometheus (optional check)
    if (Test-TcpPort -Name "Prometheus (port 9090)" -Host $VM_MAS -Port 9090) {
        $summary.VMOk++
    } else {
        Write-Host "[INFO] Prometheus (port 9090) - Not critical" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "─── VM 189 - MINDEX ($VM_MINDEX) ───" -ForegroundColor Cyan
    Write-Host ""
    
    # MINDEX API
    if (Test-HttpEndpoint -Name "MINDEX API (port 8000)" -Url "http://${VM_MINDEX}:8000/") {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    # PostgreSQL
    if (Test-TcpPort -Name "PostgreSQL (port 5432)" -Host $VM_MINDEX -Port 5432) {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    # Redis
    if (Test-TcpPort -Name "Redis (port 6379)" -Host $VM_MINDEX -Port 6379) {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    # Qdrant
    if (Test-TcpPort -Name "Qdrant (port 6333)" -Host $VM_MINDEX -Port 6333) {
        $summary.VMOk++
    } else {
        $summary.VMDown++
        $allHealthy = $false
    }
    
    Write-Host ""
}

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  SUMMARY"
Write-Host "=============================================" -ForegroundColor Cyan

if (-not $VMs) {
    $localTotal = $summary.LocalOk + $summary.LocalDown
    if ($summary.LocalDown -eq 0) {
        Write-Host "  Local:  $($summary.LocalOk)/$localTotal services OK" -ForegroundColor Green
    } else {
        Write-Host "  Local:  $($summary.LocalOk)/$localTotal services OK, $($summary.LocalDown) DOWN" -ForegroundColor Yellow
    }
}

if (-not $Local) {
    $vmTotal = $summary.VMOk + $summary.VMDown
    if ($summary.VMDown -eq 0) {
        Write-Host "  VMs:    $($summary.VMOk)/$vmTotal services OK" -ForegroundColor Green
    } else {
        Write-Host "  VMs:    $($summary.VMOk)/$vmTotal services OK, $($summary.VMDown) DOWN" -ForegroundColor Yellow
    }
}

Write-Host ""

if ($allHealthy) {
    Write-Host "  All systems operational!" -ForegroundColor Green
} else {
    Write-Host "  Some services need attention." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  To start missing local services:" -ForegroundColor Gray
    Write-Host "    .\scripts\start-dev-environment.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "  To check individual VMs:" -ForegroundColor Gray
    Write-Host "    ssh mycosoft@192.168.0.187  # Sandbox" -ForegroundColor White
    Write-Host "    ssh mycosoft@192.168.0.188  # MAS" -ForegroundColor White
    Write-Host "    ssh mycosoft@192.168.0.189  # MINDEX" -ForegroundColor White
}

Write-Host ""
