# Install MYCOSOFT services to Windows Task Scheduler
# This will auto-start all services when Windows boots

param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$TaskName = "MYCOSOFT-StartServices"
$StartScript = "$MASDir\scripts\start-all-with-watchdog.ps1"

if ($Remove) {
    Write-Host "Removing Windows Task Scheduler entry..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task removed!" -ForegroundColor Green
    exit 0
}

Write-Host "Installing MYCOSOFT startup task..." -ForegroundColor Cyan

# Create action
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`"" -WorkingDirectory $MASDir

# Create trigger (at logon and on system startup)
$trigger1 = New-ScheduledTaskTrigger -AtLogOn
$trigger2 = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# Create principal (run as current user with highest privileges)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($trigger1, $trigger2) -Settings $settings -Principal $principal -Description "Auto-start MYCOSOFT services and watchdog on Windows startup" -Force
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  Task installed successfully!              " -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "MYCOSOFT services will now start automatically:" -ForegroundColor Cyan
    Write-Host "  - When you log in" -ForegroundColor White
    Write-Host "  - When Windows starts" -ForegroundColor White
    Write-Host ""
    Write-Host "To remove this task, run:" -ForegroundColor Gray
    Write-Host "  .\scripts\install-windows-startup.ps1 -Remove" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "Error installing task: $_" -ForegroundColor Red
    exit 1
}
