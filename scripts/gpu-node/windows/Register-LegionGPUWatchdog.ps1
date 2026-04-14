#Requires -Version 5.1
<#
.SYNOPSIS
  Register a Windows Scheduled Task to run Invoke-LegionGPUWatchdog.ps1 on an interval (default: every 15 minutes).

.DESCRIPTION
  Uses modest frequency to avoid flooding the host; pairs with Register-MycosoftLegionStartup.ps1 for logon bootstrapping.

.EXAMPLE
  # On Voice Legion (Admin PowerShell):
  .\Register-LegionGPUWatchdog.ps1 -Role Voice -IntervalMinutes 15

.EXAMPLE
  # On Earth-2 Legion:
  .\Register-LegionGPUWatchdog.ps1 -Role Earth2 -IntervalMinutes 15
#>
param(
    [ValidateSet('Voice', 'Earth2')]
    [string]$Role,
    [int]$IntervalMinutes = 15,
    [switch]$Unregister
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$watch = Join-Path $here "Invoke-LegionGPUWatchdog.ps1"
$taskName = "MycosoftLegionGPUWatchdog-$Role"

if ($Unregister) {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Unregistered $taskName"
    } else {
        Write-Host "Task $taskName not found."
    }
    exit 0
}

if (-not (Test-Path $watch)) {
    throw "Missing $watch"
}

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$watch`" -Role $Role"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
# Repeating trigger: once anchor + repetition (every N minutes for 100 years — avoids MaxValue quirks)
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1))
$trigger.RepetitionInterval = New-TimeSpan -Minutes $IntervalMinutes
$trigger.RepetitionDuration = New-TimeSpan -Days 36525
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest | Out-Null
Write-Host "Registered $taskName — every $IntervalMinutes min -> Invoke-LegionGPUWatchdog -Role $Role"
