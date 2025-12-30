# MYCOSOFT Service Watchdog
# Monitors all services and automatically restarts them if they crash
# Run this script in the background to keep services running 24/7

param(
    [int]$CheckInterval = 60,  # Check every 60 seconds
    [switch]$RunOnce
)

$ErrorActionPreference = "Continue"

# Configuration
$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$WebsiteDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
$LogDir = "$MASDir\logs"
$StartupScript = "$MASDir\scripts\startup-all-services.ps1"
$WatchdogLog = "$LogDir\watchdog.log"

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Function to log messages
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Add-Content -Path $WatchdogLog -Value $logMessage
    
    if ($Level -eq "ERROR") {
        Write-Host $logMessage -ForegroundColor Red
    } elseif ($Level -eq "WARN") {
        Write-Host $logMessage -ForegroundColor Yellow
    } else {
        Write-Host $logMessage -ForegroundColor Gray
    }
}

# Function to check if a port is listening
function Test-Port {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connection
}

# Function to kill processes on a port
function Kill-PortProcess {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        if ($conn.OwningProcess) {
            try {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            } catch {
                # Ignore errors
            }
        }
    }
}

# Service definitions
$services = @(
    @{
        Name = "Website (Next.js)"
        Port = 3000
        CheckFunction = { Test-Port -Port 3000 }
        StartFunction = {
            Set-Location $WebsiteDir
            Kill-PortProcess -Port 3000
            Start-Sleep -Seconds 2
            $websiteLog = "$LogDir\website.log"
            $psCommand = "Set-Location '$WebsiteDir'; npm run dev 2>&1 | Tee-Object -FilePath '$websiteLog'"
            Start-Process powershell.exe -ArgumentList "-NoProfile", "-Command", $psCommand -WindowStyle Hidden
            Write-Log "Started Website service" "INFO"
        }
    },
    @{
        Name = "MycoBrain Service"
        Port = 8003
        CheckFunction = { Test-Port -Port 8003 }
        StartFunction = {
            Set-Location $MASDir
            Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
                try {
                    $_.CommandLine -like "*mycobrain_service*"
                } catch {
                    $false
                }
            } | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            $mycobrainLog = "$LogDir\mycobrain-service.log"
            $psCommand = "Set-Location '$MASDir'; python services\mycobrain\mycobrain_service_standalone.py 2>&1 | Tee-Object -FilePath '$mycobrainLog'"
            Start-Process powershell.exe -ArgumentList "-NoProfile", "-Command", $psCommand -WindowStyle Hidden
            Write-Log "Started MycoBrain service" "INFO"
        }
    },
    @{
        Name = "MINDEX API"
        Port = 8000
        CheckFunction = { Test-Port -Port 8000 }
        StartFunction = {
            Set-Location $MASDir
            docker-compose -f docker-compose.mindex.yml up -d 2>$null
            Write-Log "Started MINDEX containers" "INFO"
        }
    },
    @{
        Name = "MAS Orchestrator"
        Port = 8001
        CheckFunction = { Test-Port -Port 8001 }
        StartFunction = {
            Set-Location $MASDir
            docker-compose up -d 2>$null
            Write-Log "Started MAS containers" "INFO"
        }
    },
    @{
        Name = "n8n Workflows"
        Port = 5678
        CheckFunction = { Test-Port -Port 5678 }
        StartFunction = {
            Set-Location $MASDir
            docker-compose -f docker-compose.integrations.yml up -d 2>$null
            Write-Log "Started n8n containers" "INFO"
        }
    }
)

Write-Log "========================================" "INFO"
Write-Log "MYCOSOFT Service Watchdog Started" "INFO"
Write-Log "Check interval: $CheckInterval seconds" "INFO"
Write-Log "========================================" "INFO"

# Main watchdog loop
do {
    $restartCount = 0
    
    foreach ($service in $services) {
        try {
            $isRunning = & $service.CheckFunction
            
            if (-not $isRunning) {
                Write-Log "$($service.Name) is DOWN - Restarting..." "WARN"
                
                try {
                    & $service.StartFunction
                    Start-Sleep -Seconds 5
                    
                    # Verify it started
                    $isRunning = & $service.CheckFunction
                    if ($isRunning) {
                        Write-Log "$($service.Name) restarted successfully" "INFO"
                        $restartCount++
                    } else {
                        Write-Log "$($service.Name) failed to start" "ERROR"
                    }
                } catch {
                    Write-Log "Error restarting $($service.Name): $_" "ERROR"
                }
            }
        } catch {
            Write-Log "Error checking $($service.Name): $_" "ERROR"
        }
    }
    
    # Check Docker containers
    try {
        $dockerStatus = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Docker is not running - starting Docker Desktop..." "WARN"
            Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
            Start-Sleep -Seconds 30
        } else {
            # Ensure all containers have restart policies
            docker ps -q | ForEach-Object {
                docker update --restart unless-stopped $_ 2>$null
            }
        }
    } catch {
        Write-Log "Error checking Docker: $_" "ERROR"
    }
    
    if ($restartCount -gt 0) {
        Write-Log "Restarted $restartCount service(s)" "INFO"
    }
    
    if (-not $RunOnce) {
        Start-Sleep -Seconds $CheckInterval
    }
    
} while (-not $RunOnce)

Write-Log "Watchdog stopped" "INFO"
