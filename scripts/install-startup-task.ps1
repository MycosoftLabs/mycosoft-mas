# Install MYCOSOFT Docker & Services startup task
# This script creates a Windows Task Scheduler entry that starts Docker and services on boot
# RUN THIS SCRIPT AS ADMINISTRATOR

param(
    [switch]$Remove,
    [switch]$Test
)

$ErrorActionPreference = "Stop"

$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$TaskName = "MYCOSOFT-Docker-AutoStart"
$StartScript = "$MASDir\scripts\start-docker-and-services.ps1"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

if ($Remove) {
    Write-Host "Removing Windows Task Scheduler entry..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task removed!" -ForegroundColor Green
    exit 0
}

if ($Test) {
    Write-Host "Testing startup script..." -ForegroundColor Cyan
    & $StartScript -CheckOnly
    exit 0
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Installing MYCOSOFT Auto-Start Task" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Remove existing task if it exists
Write-Host "Removing any existing task..." -ForegroundColor Gray
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Create action - run PowerShell with the startup script
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$StartScript`"" `
    -WorkingDirectory $MASDir

# Create triggers:
# 1. At system startup (for services)
# 2. At user logon (backup)
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Add a delay to startup trigger to ensure network is ready
$triggerStartup.Delay = "PT30S"  # 30 second delay

# Settings for the task
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Principal - run with highest privileges
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger @($triggerStartup, $triggerLogon) `
        -Settings $settings `
        -Principal $principal `
        -Description "Automatically starts Docker Desktop and MYCOSOFT services on Windows startup. Includes 30-second delay to wait for network." `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  Task installed successfully!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Name: $TaskName" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The task will run:" -ForegroundColor White
    Write-Host "  - 30 seconds after Windows starts (to wait for network)" -ForegroundColor Gray
    Write-Host "  - When you log in (backup trigger)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "What it does:" -ForegroundColor White
    Write-Host "  1. Waits for network to be available" -ForegroundColor Gray
    Write-Host "  2. Starts Docker Desktop if not running" -ForegroundColor Gray
    Write-Host "  3. Waits for Docker to be ready (up to 5 min)" -ForegroundColor Gray
    Write-Host "  4. Starts all always-on Docker containers" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To verify the task:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Format-List" -ForegroundColor White
    Write-Host ""
    Write-Host "To test now (without restarting):" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "To remove the task:" -ForegroundColor Yellow
    Write-Host "  .\scripts\install-startup-task.ps1 -Remove" -ForegroundColor White
    Write-Host ""
    Write-Host "Logs will be written to: $MASDir\logs\" -ForegroundColor Cyan
    
} catch {
    Write-Host "Error installing task: $_" -ForegroundColor Red
    exit 1
}
