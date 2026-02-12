<#
.SYNOPSIS
    n8n Health Check and Auto-Start Script
    
.DESCRIPTION
    Checks n8n health on both local (Docker) and VM 188.
    Can auto-start Docker Desktop and n8n container if down.
    
.PARAMETER StartLocal
    Start local n8n if not running (requires Docker Desktop)
    
.PARAMETER StartDocker
    Start Docker Desktop if not running
    
.PARAMETER Sync
    Sync workflows between local and VM
    
.EXAMPLE
    .\n8n-healthcheck.ps1
    .\n8n-healthcheck.ps1 -StartLocal
    .\n8n-healthcheck.ps1 -StartDocker -StartLocal
#>

param(
    [switch]$StartLocal,
    [switch]$StartDocker,
    [switch]$Sync
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "`n=== n8n Health Check ===" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# Check Docker Desktop
Write-Host "`n[1] Docker Desktop Status" -ForegroundColor Yellow
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "    Docker Desktop: RUNNING" -ForegroundColor Green
    $dockerRunning = $true
} else {
    Write-Host "    Docker Desktop: NOT RUNNING" -ForegroundColor Red
    $dockerRunning = $false
    
    if ($StartDocker) {
        Write-Host "    Starting Docker Desktop..." -ForegroundColor Yellow
        $dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $dockerPath) {
            Start-Process $dockerPath
            Write-Host "    Waiting 45 seconds for Docker to initialize..." -ForegroundColor Gray
            Start-Sleep -Seconds 45
            
            # Recheck
            $dockerInfo = docker info 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    Docker Desktop: STARTED" -ForegroundColor Green
                $dockerRunning = $true
            } else {
                Write-Host "    Docker Desktop: FAILED TO START" -ForegroundColor Red
            }
        } else {
            Write-Host "    Docker Desktop not found at: $dockerPath" -ForegroundColor Red
        }
    }
}

# Check Local n8n
Write-Host "`n[2] Local n8n (localhost:5678)" -ForegroundColor Yellow
try {
    $localResp = Invoke-WebRequest -Uri "http://localhost:5678" -TimeoutSec 5 -UseBasicParsing
    Write-Host "    Local n8n: RUNNING (Status: $($localResp.StatusCode))" -ForegroundColor Green
    $localRunning = $true
} catch {
    Write-Host "    Local n8n: NOT RUNNING" -ForegroundColor Red
    $localRunning = $false
    
    if ($StartLocal -and $dockerRunning) {
        Write-Host "    Attempting to start n8n container..." -ForegroundColor Yellow
        
        # Check if container exists
        $container = docker ps -a --filter "name=mycosoft-n8n" --format "{{.Names}}" 2>&1
        
        if ($container -eq "mycosoft-n8n") {
            Write-Host "    Container exists. Starting..." -ForegroundColor Gray
            docker start mycosoft-n8n
        } else {
            Write-Host "    Creating new n8n container..." -ForegroundColor Gray
            docker run -d --name mycosoft-n8n `
                -p 5678:5678 `
                -v n8n_data:/home/node/.n8n `
                -e N8N_HOST=0.0.0.0 `
                -e N8N_PORT=5678 `
                -e N8N_PROTOCOL=http `
                --restart unless-stopped `
                n8nio/n8n:latest
        }
        
        Write-Host "    Waiting 15 seconds for n8n to start..." -ForegroundColor Gray
        Start-Sleep -Seconds 15
        
        # Recheck
        try {
            $localResp = Invoke-WebRequest -Uri "http://localhost:5678" -TimeoutSec 5 -UseBasicParsing
            Write-Host "    Local n8n: STARTED" -ForegroundColor Green
            $localRunning = $true
        } catch {
            Write-Host "    Local n8n: FAILED TO START" -ForegroundColor Red
        }
    } elseif ($StartLocal -and -not $dockerRunning) {
        Write-Host "    Cannot start n8n without Docker. Use -StartDocker flag." -ForegroundColor Yellow
    }
}

# Check VM n8n
Write-Host "`n[3] VM 188 n8n (192.168.0.188:5678)" -ForegroundColor Yellow
try {
    $vmResp = Invoke-WebRequest -Uri "http://192.168.0.188:5678" -TimeoutSec 10 -UseBasicParsing
    Write-Host "    VM n8n: RUNNING (Status: $($vmResp.StatusCode))" -ForegroundColor Green
    $vmRunning = $true
} catch {
    Write-Host "    VM n8n: NOT RUNNING or UNREACHABLE" -ForegroundColor Red
    $vmRunning = $false
    
    # Check if VM is reachable
    $ping = Test-Connection -ComputerName "192.168.0.188" -Count 1 -Quiet
    if ($ping) {
        Write-Host "    (VM is pingable - n8n service may be down)" -ForegroundColor Yellow
    } else {
        Write-Host "    (VM is not reachable - network issue)" -ForegroundColor Red
    }
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Docker Desktop: $(if($dockerRunning){'RUNNING'}else{'DOWN'})" -ForegroundColor $(if($dockerRunning){'Green'}else{'Red'})
Write-Host "Local n8n:      $(if($localRunning){'RUNNING'}else{'DOWN'})" -ForegroundColor $(if($localRunning){'Green'}else{'Red'})
Write-Host "VM 188 n8n:     $(if($vmRunning){'RUNNING'}else{'DOWN'})" -ForegroundColor $(if($vmRunning){'Green'}else{'Red'})

# Return status
$status = @{
    DockerDesktop = $dockerRunning
    LocalN8N = $localRunning
    VMN8N = $vmRunning
    Timestamp = (Get-Date -Format 'o')
}

if ($Sync -and $localRunning -and $vmRunning) {
    Write-Host "`n[4] Workflow Sync" -ForegroundColor Yellow
    Write-Host "    Sync requires n8n API keys. Set N8N_API_KEY and N8N_LOCAL_API_KEY env vars." -ForegroundColor Gray
    Write-Host "    Use: .\scripts\sync-n8n-workflows.ps1" -ForegroundColor Gray
}

return $status
