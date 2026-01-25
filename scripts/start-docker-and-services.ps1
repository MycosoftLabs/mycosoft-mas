# MYCOSOFT Docker & Services Auto-Start Script
# This script ensures Docker Desktop starts and all services run on PC restart
# Run this from Task Scheduler with highest privileges

param(
    [switch]$CheckOnly,
    [switch]$StopAll
)

$ErrorActionPreference = "Continue"
$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$LogFile = "$MASDir\logs\startup-$(Get-Date -Format 'yyyy-MM-dd').log"

# Ensure log directory exists
$LogDir = Split-Path $LogFile -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    Add-Content -Path $LogFile -Value $logEntry -ErrorAction SilentlyContinue
}

function Test-DockerRunning {
    try {
        $result = docker info 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Start-DockerDesktop {
    Write-Log "Checking Docker Desktop status..."
    
    if (Test-DockerRunning) {
        Write-Log "Docker Desktop is already running" "SUCCESS"
        return $true
    }
    
    Write-Log "Docker Desktop not running, attempting to start..."
    
    # Find Docker Desktop executable
    $dockerPaths = @(
        "C:\Program Files\Docker\Docker\Docker Desktop.exe",
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    
    $dockerExe = $null
    foreach ($path in $dockerPaths) {
        if (Test-Path $path) {
            $dockerExe = $path
            break
        }
    }
    
    if (-not $dockerExe) {
        Write-Log "Docker Desktop executable not found!" "ERROR"
        return $false
    }
    
    Write-Log "Starting Docker Desktop from: $dockerExe"
    Start-Process -FilePath $dockerExe -WindowStyle Minimized
    
    # Wait for Docker to be ready (max 5 minutes)
    $maxWait = 300
    $waited = 0
    $checkInterval = 10
    
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds $checkInterval
        $waited += $checkInterval
        Write-Log "Waiting for Docker... ($waited/$maxWait seconds)"
        
        if (Test-DockerRunning) {
            Write-Log "Docker Desktop is now running!" "SUCCESS"
            # Give it a few more seconds to fully initialize
            Start-Sleep -Seconds 5
            return $true
        }
    }
    
    Write-Log "Docker Desktop failed to start within $maxWait seconds" "ERROR"
    return $false
}

function Start-AlwaysOnServices {
    Write-Log "Starting Always-On services..."
    
    Set-Location $MASDir
    
    # Create network if needed
    docker network create mycosoft-network 2>$null
    
    # Start always-on stack
    Write-Log "Starting always-on Docker Compose stack..."
    $result = docker-compose -f docker-compose.always-on.yml up -d 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Always-on services started successfully" "SUCCESS"
    } else {
        Write-Log "Error starting always-on services: $result" "ERROR"
    }
    
    # List running containers
    Write-Log "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | ForEach-Object { Write-Log $_ }
}

function Get-ServiceStatus {
    Write-Log "=== Service Status ===" "INFO"
    
    # Check Docker
    if (Test-DockerRunning) {
        Write-Log "Docker: RUNNING" "SUCCESS"
    } else {
        Write-Log "Docker: NOT RUNNING" "ERROR"
    }
    
    # List containers
    Write-Log "Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1 | ForEach-Object { Write-Log $_ }
}

# Main execution
Write-Log "============================================"
Write-Log "  MYCOSOFT Docker & Services Startup"
Write-Log "  Script started at: $(Get-Date)"
Write-Log "============================================"

if ($CheckOnly) {
    Get-ServiceStatus
    exit 0
}

if ($StopAll) {
    Write-Log "Stopping all services..."
    Set-Location $MASDir
    docker-compose -f docker-compose.always-on.yml down 2>$null
    docker-compose down 2>$null
    Write-Log "All services stopped" "SUCCESS"
    exit 0
}

# Step 1: Start Docker Desktop
$dockerStarted = Start-DockerDesktop

if (-not $dockerStarted) {
    Write-Log "Cannot proceed without Docker Desktop" "ERROR"
    exit 1
}

# Step 2: Start always-on services
Start-AlwaysOnServices

# Step 3: Show status
Get-ServiceStatus

Write-Log "============================================"
Write-Log "  Startup Complete!"
Write-Log "============================================"
