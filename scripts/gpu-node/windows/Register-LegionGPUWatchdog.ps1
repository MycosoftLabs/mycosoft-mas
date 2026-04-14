#Requires -Version 5.1
<#
.SYNOPSIS
  Register a Windows Scheduled Task to run Invoke-LegionGPUWatchdog.ps1 on an interval (default: every 15 minutes).

.DESCRIPTION
  Uses schtasks.exe (works across PS versions). Pairs with Register-MycosoftLegionStartup.ps1 for logon bootstrapping.

.EXAMPLE
  .\Register-LegionGPUWatchdog.ps1 -Role Voice -IntervalMinutes 15
.EXAMPLE
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
    schtasks /Delete /TN $taskName /F 2>$null
    Write-Host "Removed task $taskName (if it existed)."
    exit 0
}

if (-not (Test-Path $watch)) {
    throw "Missing $watch"
}

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$watch`" -Role $Role"
$tr = "powershell.exe $arg"
# /RL HIGHEST may require Admin; omit for current-user context
$null = schtasks /Create /F /TN $taskName /TR $tr /SC MINUTE /MO $IntervalMinutes
Write-Host "Registered scheduled task $taskName every $IntervalMinutes minutes (schtasks)."
