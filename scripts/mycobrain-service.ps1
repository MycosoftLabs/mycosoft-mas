<#
.SYNOPSIS
    MycoBrain Service Manager - Always-on 24/7/365 service management

.DESCRIPTION
    Manages the MycoBrain service which provides:
    - Serial communication with MycoBrain hardware
    - Heartbeat registration to MAS Device Registry  
    - Network-wide device visibility
    - Gateway for LoRa, Bluetooth, WiFi ingestion

.PARAMETER Action
    start    - Start the service in background
    stop     - Stop the service (only for debugging)
    restart  - Restart the service
    status   - Check if running
    health   - Full health check with device info
    logs     - View recent logs

.PARAMETER Schedule
    Install Windows scheduled task for auto-start on boot/login

.EXAMPLE
    .\mycobrain-service.ps1 start
    .\mycobrain-service.ps1 status
    .\mycobrain-service.ps1 -Schedule
#>

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "health", "logs")]
    [string]$Action = "status",
    
    [switch]$Schedule
)

$ErrorActionPreference = "Continue"
$ServiceName = "MycoBrain Service"
$ServicePort = 8003
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$ServiceScript = Join-Path $RepoRoot "services\mycobrain\mycobrain_service_standalone.py"
$LogFile = Join-Path $RepoRoot "data\mycobrain_service.log"
$PidFile = Join-Path $RepoRoot "data\mycobrain_service.pid"
$TaskName = "Mycosoft-MycoBrainService"

# Ensure data directory exists
$DataDir = Join-Path $RepoRoot "data"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

function Get-ServicePid {
    if (Test-Path $PidFile) {
        $pid = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($pid -and ($pid.ToString().Trim() -match '^\d+$')) {
            try {
                $proc = Get-Process -Id ([int]$pid) -ErrorAction SilentlyContinue
                if ($proc) {
                    return [int]$pid
                }
            } catch {
                # Ignore errors, fall through to fallback below
            }
        }
    }
    # Fallback: find by port
    $conn = Get-NetTCPConnection -LocalPort $ServicePort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($conn) {
        return $conn.OwningProcess
    }
    return $null
}
                }
            } catch {
                # Ignore errors, fall through to fallback below
            }
        }
    }
    # Fallback: find by port
    $conn = Get-NetTCPConnection -LocalPort $ServicePort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($conn) {
        return $conn.OwningProcess
    }
    return $null
}

function Test-ServiceRunning {
    $pid = Get-ServicePid
    if ($pid) {
        return $true
    }
    return $false
}

function Test-ServiceHealth {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$ServicePort/health" -TimeoutSec 5 -ErrorAction Stop
        return $response
    } catch {
        return $null
    }
}

function Start-MycoBrainService {
    if (Test-ServiceRunning) {
        Write-Host "[OK] $ServiceName is already running" -ForegroundColor Green
        return $true
    }
    
    # Kill any process holding the port
    $portHolder = Get-NetTCPConnection -LocalPort $ServicePort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($portHolder) {
        Write-Host "[WARN] Port $ServicePort in use by PID $($portHolder.OwningProcess), killing..." -ForegroundColor Yellow
        Stop-Process -Id $portHolder.OwningProcess -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
    
    Write-Host "[INFO] Starting $ServiceName..." -ForegroundColor Cyan
    
    # Find Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Host "[ERROR] Python not found in PATH" -ForegroundColor Red
        return $false
    }
    
    # Check if service script exists
    if (-not (Test-Path $ServiceScript)) {
        Write-Host "[ERROR] Service script not found: $ServiceScript" -ForegroundColor Red
        return $false
    }
    
    # Start in background
    $process = Start-Process -FilePath $python.Source -ArgumentList $ServiceScript `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $LogFile -RedirectStandardError "$LogFile.err"
    
    if ($process) {
        $process.Id | Out-File $PidFile -Force
        Write-Host "[OK] Started $ServiceName (PID: $($process.Id))" -ForegroundColor Green
        
        # Wait for health check
        Start-Sleep -Seconds 2
        $health = Test-ServiceHealth
        if ($health) {
            Write-Host "[OK] Health check passed - $($health.devices_connected) device(s) connected" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[WARN] Service started but health check pending..." -ForegroundColor Yellow
            return $true
        }
    } else {
        Write-Host "[ERROR] Failed to start $ServiceName" -ForegroundColor Red
        return $false
    }
}

function Stop-MycoBrainService {
    $pid = Get-ServicePid
    if (-not $pid) {
        Write-Host "[INFO] $ServiceName is not running" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "[INFO] Stopping $ServiceName (PID: $pid)..." -ForegroundColor Cyan
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    
    if (Test-Path $PidFile) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
    
    Start-Sleep -Seconds 1
    if (-not (Test-ServiceRunning)) {
        Write-Host "[OK] $ServiceName stopped" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[WARN] Service may still be running" -ForegroundColor Yellow
        return $false
    }
}

function Show-ServiceStatus {
    $pid = Get-ServicePid
    if ($pid) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        Write-Host "[OK] $ServiceName is RUNNING" -ForegroundColor Green
        Write-Host "     PID: $pid" -ForegroundColor Gray
        Write-Host "     Port: $ServicePort" -ForegroundColor Gray
        if ($process) {
            Write-Host "     Memory: $([math]::Round($process.WorkingSet64 / 1MB, 1)) MB" -ForegroundColor Gray
            Write-Host "     Uptime: $([math]::Round((Get-Date) - $process.StartTime).TotalHours, 1)) hours" -ForegroundColor Gray
        }
        return $true
    } else {
        Write-Host "[OFFLINE] $ServiceName is NOT RUNNING" -ForegroundColor Red
        Write-Host "     Run: .\scripts\mycobrain-service.ps1 start" -ForegroundColor Yellow
        return $false
    }
}

function Show-ServiceHealth {
    $health = Test-ServiceHealth
    if ($health) {
        Write-Host "[HEALTH CHECK]" -ForegroundColor Cyan
        Write-Host "  Status: $($health.status)" -ForegroundColor $(if ($health.status -eq "ok") { "Green" } else { "Yellow" })
        Write-Host "  Version: $($health.version)" -ForegroundColor Gray
        Write-Host "  Devices Connected: $($health.devices_connected)" -ForegroundColor $(if ($health.devices_connected -gt 0) { "Green" } else { "Yellow" })
        Write-Host "  Timestamp: $($health.timestamp)" -ForegroundColor Gray
        
        # Get device details
        try {
            $devices = Invoke-RestMethod -Uri "http://localhost:$ServicePort/devices" -TimeoutSec 5 -ErrorAction Stop
            if ($devices) {
                Write-Host "`n[CONNECTED DEVICES]" -ForegroundColor Cyan
                foreach ($device in $devices) {
                    Write-Host "  - $($device.port): $($device.status)" -ForegroundColor Gray
                }
            }
        } catch {
            Write-Host "  (Could not fetch device details)" -ForegroundColor Yellow
        }
        return $true
    } else {
        Write-Host "[HEALTH CHECK FAILED]" -ForegroundColor Red
        Write-Host "  Service not responding on port $ServicePort" -ForegroundColor Yellow
        Show-ServiceStatus
        return $false
    }
}

function Show-ServiceLogs {
    if (Test-Path $LogFile) {
        Write-Host "[RECENT LOGS] (last 50 lines)" -ForegroundColor Cyan
        Get-Content $LogFile -Tail 50
    } else {
        Write-Host "[INFO] No log file found at $LogFile" -ForegroundColor Yellow
    }
    
    if (Test-Path "$LogFile.err") {
        $errContent = Get-Content "$LogFile.err" -Tail 20 -ErrorAction SilentlyContinue
        if ($errContent) {
            Write-Host "`n[RECENT ERRORS]" -ForegroundColor Red
            $errContent
        }
    }
}

function Install-ScheduledTask {
    Write-Host "[INFO] Installing scheduled task for auto-start..." -ForegroundColor Cyan
    
    $scriptPath = $MyInvocation.PSCommandPath
    if (-not $scriptPath) {
        $scriptPath = Join-Path $ScriptRoot "mycobrain-service.ps1"
    }
    
    # Remove existing task if present
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[INFO] Removed existing task" -ForegroundColor Yellow
    }
    
    # Create action
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" start"
    
    # Create triggers: at startup and at user logon
    $triggerStartup = New-ScheduledTaskTrigger -AtStartup
    $triggerLogon = New-ScheduledTaskTrigger -AtLogOn
    
    # Create settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    
    # Register task
    $task = Register-ScheduledTask -TaskName $TaskName -Action $action `
        -Trigger $triggerStartup, $triggerLogon -Settings $settings `
        -Description "MycoBrain 24/7/365 always-on service for device communication" `
        -RunLevel Highest
    
    if ($task) {
        Write-Host "[OK] Scheduled task '$TaskName' installed" -ForegroundColor Green
        Write-Host "     Triggers: At startup, At logon" -ForegroundColor Gray
        Write-Host "     Auto-restart: 3 attempts, 1 minute interval" -ForegroundColor Gray
        return $true
    } else {
        Write-Host "[ERROR] Failed to install scheduled task" -ForegroundColor Red
        return $false
    }
}

# Main logic
if ($Schedule) {
    Install-ScheduledTask
    exit
}

switch ($Action) {
    "start" {
        Start-MycoBrainService
    }
    "stop" {
        Write-Host "[WARN] Stopping MycoBrain service - remember to restart after debugging!" -ForegroundColor Yellow
        Stop-MycoBrainService
    }
    "restart" {
        Stop-MycoBrainService
        Start-Sleep -Seconds 1
        Start-MycoBrainService
    }
    "status" {
        Show-ServiceStatus
    }
    "health" {
        Show-ServiceHealth
    }
    "logs" {
        Show-ServiceLogs
    }
    default {
        Show-ServiceStatus
    }
}
