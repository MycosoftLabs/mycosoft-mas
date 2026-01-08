# MYCOSOFT Service Watchdog
# Monitors and automatically restarts services if they go down
# Run this script to keep all services running persistently

param(
    [int]$CheckInterval = 30,  # Check every 30 seconds
    [switch]$StartNow = $false  # Start services immediately if not running
)

$ErrorActionPreference = "Continue"

# Configuration
$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$WebsiteDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
$LogDir = "$MASDir\logs"

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$WatchdogLog = "$LogDir\watchdog.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path $WatchdogLog -Value $logMessage
    Write-Host $logMessage
}

function Test-Port {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return $null -ne $connection
    } catch {
        return $false
    }
}

function Start-Website {
    Write-Log "Starting Website on port 3000..."
    Set-Location $WebsiteDir
    
    # Kill existing processes on port 3000
    $existing = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($existing) {
        $existing | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
    }
    
    $websiteLog = "$LogDir\website.log"
    $psCommand = "Set-Location '$WebsiteDir'; npm run dev 2>&1 | Tee-Object -FilePath '$websiteLog'"
    
    Start-Process powershell.exe -ArgumentList "-NoProfile", "-Command", $psCommand -WindowStyle Hidden
    Start-Sleep -Seconds 10
    
    if (Test-Port 3000) {
        Write-Log "Website started successfully"
        return $true
    } else {
        Write-Log "WARNING: Website may not have started correctly"
        return $false
    }
}

function Start-MycoBrain {
    Write-Log "Starting MycoBrain service on port 8003..."
    Set-Location $MASDir
    
    # Kill existing MycoBrain processes
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -like "*mycobrain_service*"
        } catch {
            $false
        }
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Start-Sleep -Seconds 2
    
    $mycobrainLog = "$LogDir\mycobrain-service.log"
    $psCommand = "Set-Location '$MASDir'; python services\mycobrain\mycobrain_service_standalone.py 2>&1 | Tee-Object -FilePath '$mycobrainLog'"
    
    Start-Process powershell.exe -ArgumentList "-NoProfile", "-Command", $psCommand -WindowStyle Hidden
    Start-Sleep -Seconds 5
    
    if (Test-Port 8003) {
        Write-Log "MycoBrain service started successfully"
        return $true
    } else {
        Write-Log "WARNING: MycoBrain service may not have started"
        return $false
    }
}

function Start-DockerContainers {
    Write-Log "Checking Docker containers..."
    Set-Location $MASDir
    
    # Check if Docker is running
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Docker is not running. Attempting to start Docker Desktop..."
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 30
    }
    
    # Create network if needed
    docker network create mycosoft-network 2>$null | Out-Null
    
    # Start containers
    docker-compose up -d 2>$null | Out-Null
    docker-compose -f docker-compose.mindex.yml up -d 2>$null | Out-Null
    docker-compose -f docker-compose.integrations.yml up -d 2>$null | Out-Null
    
    # Set restart policies
    docker ps -q | ForEach-Object { docker update --restart unless-stopped $_ 2>$null | Out-Null }
    
    Write-Log "Docker containers checked/started"
}

# Service definitions
$Services = @(
    @{
        Name = "Website"
        Port = 3000
        StartFunction = { Start-Website }
        Required = $true
    },
    @{
        Name = "MycoBrain Service"
        Port = 8003
        StartFunction = { Start-MycoBrain }
        Required = $true
    },
    @{
        Name = "MINDEX API"
        Port = 8000
        StartFunction = { Start-DockerContainers }
        Required = $false
    },
    @{
        Name = "MAS Orchestrator"
        Port = 8001
        StartFunction = { Start-DockerContainers }
        Required = $false
    },
    @{
        Name = "n8n Workflows"
        Port = 5678
        StartFunction = { Start-DockerContainers }
        Required = $false
    }
)

Write-Log "============================================"
Write-Log "MYCOSOFT Service Watchdog Started"
Write-Log "Check interval: $CheckInterval seconds"
Write-Log "============================================"

# Initial start if requested
if ($StartNow) {
    Write-Log "Starting all services initially..."
    foreach ($service in $Services) {
        if (-not (Test-Port $service.Port)) {
            Write-Log "Service $($service.Name) not running, starting..."
            & $service.StartFunction
            Start-Sleep -Seconds 5
        }
    }
}

# Main monitoring loop
$iteration = 0
while ($true) {
    $iteration++
    
    foreach ($service in $Services) {
        $isRunning = Test-Port $service.Port
        
        if (-not $isRunning) {
            Write-Log "ALERT: $($service.Name) (port $($service.Port)) is DOWN - Restarting..."
            
            try {
                & $service.StartFunction
                Start-Sleep -Seconds 5
                
                # Verify restart
                if (Test-Port $service.Port) {
                    Write-Log "SUCCESS: $($service.Name) restarted successfully"
                } else {
                    Write-Log "ERROR: Failed to restart $($service.Name)"
                }
            } catch {
                Write-Log "ERROR restarting $($service.Name): $_"
            }
        } elseif ($iteration % 20 -eq 0) {
            # Log status every 20 iterations (10 minutes at 30s intervals)
            Write-Log "OK: $($service.Name) is running"
        }
    }
    
    # Check Docker containers every 5 minutes
    if ($iteration % 10 -eq 0) {
        try {
            $containers = docker ps --format "{{.Names}}" 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Log "WARNING: Docker may not be running"
            } else {
                $containerCount = ($containers | Measure-Object).Count
                if ($containerCount -lt 5) {
                    Write-Log "WARNING: Only $containerCount Docker containers running (expected more)"
                    Start-DockerContainers
                }
            }
        } catch {
            Write-Log "ERROR checking Docker: $_"
        }
    }
    
    Start-Sleep -Seconds $CheckInterval
}





























