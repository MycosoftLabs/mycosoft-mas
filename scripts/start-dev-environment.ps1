# Start Development Environment (Feb 12, 2026)
# One command to start all required local services for Mycosoft development.
#
# This script starts:
#   1. Docker Desktop (if not running) - required for n8n
#   2. n8n local container (port 5678) - workflow automation
#   3. MycoBrain Service (port 8003) - device communication
#   4. Cursor Sync Watcher - syncs rules/agents/skills
#   5. Notion Docs Watcher - syncs docs to Notion
#
# Usage:
#   .\scripts\start-dev-environment.ps1           # Start all services
#   .\scripts\start-dev-environment.ps1 -NoDocker # Skip Docker/n8n (for VM-only testing)
#   .\scripts\start-dev-environment.ps1 -Status   # Just check status, don't start
#
# After running, the dev website can be started with:
#   cd ..\WEBSITE\website && npm run dev:next-only

param(
    [switch]$NoDocker,
    [switch]$Status
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT DEVELOPMENT ENVIRONMENT"
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ── Helper Functions ──────────────────────────────────────────────────────────

function Test-DockerRunning {
    try {
        $dockerInfo = docker info 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Start-DockerDesktop {
    Write-Host "[1/5] Docker Desktop..." -ForegroundColor Yellow
    
    if (Test-DockerRunning) {
        Write-Host "      Already running" -ForegroundColor Green
        return $true
    }
    
    # Try to start Docker Desktop
    $dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Write-Host "      Starting Docker Desktop..." -ForegroundColor Yellow
        Start-Process $dockerPath
        
        # Wait for Docker to be ready (max 60 seconds)
        $maxWait = 60
        $waited = 0
        while (-not (Test-DockerRunning) -and $waited -lt $maxWait) {
            Start-Sleep -Seconds 2
            $waited += 2
            Write-Host "      Waiting for Docker... ($waited s)" -ForegroundColor Gray
        }
        
        if (Test-DockerRunning) {
            Write-Host "      Docker is ready" -ForegroundColor Green
            return $true
        } else {
            Write-Host "      Docker did not start in time" -ForegroundColor Red
            return $false
        }
    } else {
        Write-Host "      Docker Desktop not found at $dockerPath" -ForegroundColor Red
        return $false
    }
}

function Start-N8nContainer {
    Write-Host "[2/5] n8n Local Container (port 5678)..." -ForegroundColor Yellow
    
    # Check if n8n is already running
    $n8nContainer = docker ps --filter "name=mycosoft-n8n" --format "{{.Names}}" 2>$null
    if ($n8nContainer -eq "mycosoft-n8n") {
        Write-Host "      Already running" -ForegroundColor Green
        return
    }
    
    # Check if container exists but is stopped
    $n8nStopped = docker ps -a --filter "name=mycosoft-n8n" --format "{{.Names}}" 2>$null
    if ($n8nStopped -eq "mycosoft-n8n") {
        Write-Host "      Starting existing container..." -ForegroundColor Yellow
        docker start mycosoft-n8n 2>$null
    } else {
        # Use the n8n healthcheck script if available
        $n8nScript = Join-Path $ProjectRoot "scripts\n8n-healthcheck.ps1"
        if (Test-Path $n8nScript) {
            Write-Host "      Using n8n-healthcheck.ps1..." -ForegroundColor Yellow
            & $n8nScript -StartLocal
        } else {
            Write-Host "      n8n container not found. Run: docker pull n8nio/n8n" -ForegroundColor Yellow
        }
    }
    
    # Verify
    Start-Sleep -Seconds 2
    $n8nRunning = docker ps --filter "name=mycosoft-n8n" --format "{{.Names}}" 2>$null
    if ($n8nRunning -eq "mycosoft-n8n") {
        Write-Host "      Running on http://localhost:5678" -ForegroundColor Green
    } else {
        Write-Host "      Could not start n8n" -ForegroundColor Red
    }
}

function Start-MycoBrainService {
    Write-Host "[3/5] MycoBrain Service (port 8003)..." -ForegroundColor Yellow
    
    # Check if already running
    $conn = Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($conn) {
        Write-Host "      Already running (PID: $($conn.OwningProcess))" -ForegroundColor Green
        return
    }
    
    # Start using the mycobrain-service script
    $mcbScript = Join-Path $ProjectRoot "scripts\mycobrain-service.ps1"
    if (Test-Path $mcbScript) {
        & $mcbScript start
        Start-Sleep -Seconds 2
        
        $conn = Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        if ($conn) {
            Write-Host "      Running on http://localhost:8003" -ForegroundColor Green
        } else {
            Write-Host "      Could not verify startup" -ForegroundColor Yellow
        }
    } else {
        Write-Host "      mycobrain-service.ps1 not found" -ForegroundColor Red
    }
}

function Start-CursorSyncWatcher {
    Write-Host "[4/5] Cursor Sync Watcher..." -ForegroundColor Yellow
    
    # Check if already running
    $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | 
        Where-Object { $_.CommandLine -like "*sync_cursor_system*--watch*" }
    
    if ($procs) {
        Write-Host "      Already running (PID: $($procs.ProcessId))" -ForegroundColor Green
        return
    }
    
    # Start in background
    $syncScript = Join-Path $ProjectRoot "scripts\sync_cursor_system.py"
    if (Test-Path $syncScript) {
        Start-Process -FilePath "python" -ArgumentList $syncScript, "--watch" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | 
            Where-Object { $_.CommandLine -like "*sync_cursor_system*" }
        if ($procs) {
            Write-Host "      Running (syncs every 30s)" -ForegroundColor Green
        } else {
            Write-Host "      Could not verify startup" -ForegroundColor Yellow
        }
    } else {
        Write-Host "      sync_cursor_system.py not found" -ForegroundColor Red
    }
}

function Start-NotionDocsWatcher {
    Write-Host "[5/5] Notion Docs Watcher..." -ForegroundColor Yellow
    
    # Check if already running
    $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | 
        Where-Object { $_.CommandLine -like "*notion_docs_watcher*" }
    
    if ($procs) {
        Write-Host "      Already running (PID: $($procs.ProcessId))" -ForegroundColor Green
        return
    }
    
    # Start using notion-sync script
    $notionScript = Join-Path $ProjectRoot "scripts\notion-sync.ps1"
    if (Test-Path $notionScript) {
        & $notionScript watch-bg
        Start-Sleep -Seconds 2
        
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | 
            Where-Object { $_.CommandLine -like "*notion_docs_watcher*" }
        if ($procs) {
            Write-Host "      Running" -ForegroundColor Green
        } else {
            Write-Host "      Could not verify startup" -ForegroundColor Yellow
        }
    } else {
        Write-Host "      notion-sync.ps1 not found" -ForegroundColor Red
    }
}

function Show-Status {
    Write-Host "Service Status:" -ForegroundColor Cyan
    Write-Host ""
    
    # Docker
    if (Test-DockerRunning) {
        Write-Host "[OK]   Docker Desktop" -ForegroundColor Green
    } else {
        Write-Host "[DOWN] Docker Desktop" -ForegroundColor Red
    }
    
    # n8n
    $n8n = docker ps --filter "name=mycosoft-n8n" --format "{{.Names}}" 2>$null
    if ($n8n -eq "mycosoft-n8n") {
        Write-Host "[OK]   n8n (port 5678)" -ForegroundColor Green
    } else {
        Write-Host "[DOWN] n8n (port 5678)" -ForegroundColor Red
    }
    
    # MycoBrain
    $mcb = Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($mcb) {
        Write-Host "[OK]   MycoBrain Service (port 8003)" -ForegroundColor Green
    } else {
        Write-Host "[DOWN] MycoBrain Service (port 8003)" -ForegroundColor Red
    }
    
    # Cursor Sync
    $sync = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | 
        Where-Object { $_.CommandLine -like "*sync_cursor_system*" }
    if ($sync) {
        Write-Host "[OK]   Cursor Sync Watcher" -ForegroundColor Green
    } else {
        Write-Host "[DOWN] Cursor Sync Watcher" -ForegroundColor Red
    }
    
    # Notion
    $notion = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | 
        Where-Object { $_.CommandLine -like "*notion_docs_watcher*" }
    if ($notion) {
        Write-Host "[OK]   Notion Docs Watcher" -ForegroundColor Green
    } else {
        Write-Host "[DOWN] Notion Docs Watcher" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ── Main ──────────────────────────────────────────────────────────────────────

if ($Status) {
    Show-Status
    exit 0
}

# Start services
if (-not $NoDocker) {
    $dockerOk = Start-DockerDesktop
    if ($dockerOk) {
        Start-N8nContainer
    } else {
        Write-Host "[2/5] n8n - SKIPPED (Docker not running)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[1/5] Docker Desktop - SKIPPED (-NoDocker)" -ForegroundColor Gray
    Write-Host "[2/5] n8n - SKIPPED (-NoDocker)" -ForegroundColor Gray
}

Start-MycoBrainService
Start-CursorSyncWatcher
Start-NotionDocsWatcher

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Development environment ready!"
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    cd ..\WEBSITE\website"
Write-Host "    npm run dev:next-only"
Write-Host ""
Write-Host "  Website will be at: http://localhost:3010"
Write-Host "  VMs: MAS=188:8001, MINDEX=189:8000"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
