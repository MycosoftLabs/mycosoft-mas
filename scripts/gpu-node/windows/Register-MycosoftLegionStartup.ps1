#Requires -Version 5.1
<#
.SYNOPSIS
  Register Windows Scheduled Tasks to run voice stack and/or Earth2 API at user logon (delayed).

.EXAMPLE
  # Voice Legion (192.168.0.241) - run as Admin once:
  .\Register-MycosoftLegionStartup.ps1 -Role Voice

.EXAMPLE
  # Earth2 Legion (192.168.0.249):
  .\Register-MycosoftLegionStartup.ps1 -Role Earth2
#>
param(
    [ValidateSet('Voice', 'Earth2')]
    [string]$Role,
    [int]$DelaySeconds = 90
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$voicePs1 = Join-Path $here "Start-LegionVoice-24x7.ps1"
$earthPs1 = Join-Path $here "Start-LegionEarth2API-24x7.ps1"

if ($Role -eq 'Voice') {
    $name = "MycosoftLegionVoice24x7"
    $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$voicePs1`" -SkipIfRunning"
} else {
    $name = "MycosoftLegionEarth2API24x7"
    $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$earthPs1`""
}

$existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
try {
    $trigger.Delay = [TimeSpan]::FromSeconds($DelaySeconds)
} catch {
    Write-Warning "Trigger.Delay not set ($($_.Exception.Message)); task runs immediately at logon."
}
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest | Out-Null
Write-Host "Registered scheduled task: $name (delay ${DelaySeconds}s at logon)."
