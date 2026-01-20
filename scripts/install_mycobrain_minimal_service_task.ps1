$ErrorActionPreference = "Stop"

$taskName = "Mycosoft-MycoBrain-Minimal"
$repoRoot = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $repoRoot "scripts\start_mycobrain_minimal_service.ps1"

if (-not (Test-Path $startScript)) {
  Write-Host "ERROR: Start script not found: $startScript" -ForegroundColor Red
  exit 1
}

Write-Host "Installing Scheduled Task: $taskName" -ForegroundColor Cyan

try { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null } catch {}

$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Runs MycoBrain Minimal Service on port 8003 for sandbox routing." | Out-Null

Write-Host "[OK] Scheduled Task installed." -ForegroundColor Green
Write-Host "Start it now with:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName `"$taskName`"" -ForegroundColor White

