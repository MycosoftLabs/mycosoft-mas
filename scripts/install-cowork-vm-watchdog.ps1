# install-cowork-vm-watchdog.ps1
# Creates Windows scheduled task: Cowork VM watchdog runs at startup + every 2 minutes.
# Run as Administrator. MAR04 2026

#Requires -RunAsAdministrator

$taskName = "Mycosoft-CoworkVMWatchdog"
$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$watchdogScript = Join-Path $scriptDir "ensure-cowork-vm-watchdog.ps1"
$logDir = "$env:LOCALAPPDATA\Mycosoft\cowork-watchdog"

if (-not (Test-Path $watchdogScript)) {
    Write-Host "ERROR: $watchdogScript not found" -ForegroundColor Red
    exit 1
}

# Remove existing task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create task: run at logon + every 2 minutes
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdogScript`""
$trigger1 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# Use 1-year duration - MaxValue is rejected by Task Scheduler
$trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration (New-TimeSpan -Days 365)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger1,$trigger2 -Principal $principal -Settings $settings -Force | Out-Null

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

Write-Host "Cowork VM watchdog installed:" -ForegroundColor Green
Write-Host "  - Runs at logon" -ForegroundColor Gray
Write-Host "  - Runs every 2 minutes" -ForegroundColor Gray
Write-Host "  - Log: $logDir\watchdog.log" -ForegroundColor Gray
Write-Host ""
Write-Host "Run watchdog now to fix if service is down:" -ForegroundColor Yellow
& $watchdogScript
