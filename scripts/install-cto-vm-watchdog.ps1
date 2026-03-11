# install-cto-vm-watchdog.ps1
# Registers CTO VM 194 scheduled tasks for 24/7 autonomy.
# Run as Administrator on CTO VM after bootstrap. MAR08 2026
# Tasks: CTO Watchdog (logon + 2 min), Cursor sync (30 min), Workspace sync (15 min), Operating report (10 min).
# Note: csuite_heartbeat (1 min) is already registered by bootstrap_guest_remote.

#Requires -RunAsAdministrator

$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$masRepo = Split-Path $scriptDir -Parent
$infraCsuite = Join-Path $masRepo "infra\csuite"
$ensureScript = Join-Path $scriptDir "ensure-cto-vm-watchdog.ps1"
$forgeBridge = Join-Path $infraCsuite "forge_bridge_run.ps1"
$forgeReport = Join-Path $infraCsuite "forge_operating_report.ps1"
$syncScript = Join-Path $masRepo "scripts\sync_cursor_system.py"
$CodeRoot = $env:CTO_CODE_ROOT; if (-not $CodeRoot) { $CodeRoot = "C:\Users\$env:USERNAME\Mycosoft\CODE" }
$masRepoPath = Join-Path $CodeRoot "MAS\mycosoft-mas"

if (-not (Test-Path $ensureScript)) {
    Write-Host "ERROR: $ensureScript not found" -ForegroundColor Red
    exit 1
}

# --- 1. CTO Watchdog (logon + every 2 min) ---
$taskName = "Mycosoft-CTO-Watchdog"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ensureScript`""
$trigger1 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration (New-TimeSpan -Days 365)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger1,$trigger2 -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "[CTO] Task registered: $taskName (logon + every 2 min)" -ForegroundColor Green

# --- 2. Cursor system sync (every 30 min) ---
$taskName2 = "Mycosoft-CTO-CursorSync"
Unregister-ScheduledTask -TaskName $taskName2 -Confirm:$false -ErrorAction SilentlyContinue
$syncAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command `"Set-Location '$masRepoPath'; `$env:CODE_ROOT='$CodeRoot'; python '$syncScript' 2>&1 | Out-Null`""
$syncTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 365)
Register-ScheduledTask -TaskName $taskName2 -Action $syncAction -Trigger $syncTrigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "[CTO] Task registered: $taskName2 (every 30 min)" -ForegroundColor Green

# --- 3. Workspace sync / git pull (every 15 min) ---
$taskName3 = "Mycosoft-CTO-WorkspaceSync"
$wsScript = @"
Set-Location '$masRepoPath'
git pull origin main 2>&1 | Out-Null
"@
$wsTemp = "$env:TEMP\cto_workspace_sync.ps1"
$wsScript | Out-File -FilePath $wsTemp -Encoding utf8
Unregister-ScheduledTask -TaskName $taskName3 -Confirm:$false -ErrorAction SilentlyContinue
$wsAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$wsTemp`""
$wsTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 365)
Register-ScheduledTask -TaskName $taskName3 -Action $wsAction -Trigger $wsTrigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "[CTO] Task registered: $taskName3 (every 15 min)" -ForegroundColor Green

# --- 4. Operating report (every 10 min) ---
if (Test-Path $forgeReport) {
    $taskName4 = "Mycosoft-CTO-OperatingReport"
    Unregister-ScheduledTask -TaskName $taskName4 -Confirm:$false -ErrorAction SilentlyContinue
    $reportAction = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$forgeReport`" -Silent"
    $reportTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 365)
    Register-ScheduledTask -TaskName $taskName4 -Action $reportAction -Trigger $reportTrigger -Principal $principal -Settings $settings -Force | Out-Null
    Write-Host "[CTO] Task registered: $taskName4 (every 10 min)" -ForegroundColor Green
} else {
    Write-Host "[CTO] forge_operating_report.ps1 not found — skipping operating report task" -ForegroundColor Yellow
}

$logDir = "$env:LOCALAPPDATA\Mycosoft\cto-watchdog"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

Write-Host ""
Write-Host "CTO VM watchdog installed:" -ForegroundColor Green
Write-Host "  - CTO Watchdog: logon + every 2 min (OpenClaw check, enriched heartbeat)" -ForegroundColor Gray
Write-Host "  - Cursor sync: every 30 min" -ForegroundColor Gray
Write-Host "  - Workspace sync: every 15 min" -ForegroundColor Gray
Write-Host "  - Operating report: every 10 min" -ForegroundColor Gray
Write-Host "  - Log: $logDir\watchdog.log" -ForegroundColor Gray
Write-Host ""
Write-Host "Run watchdog now:" -ForegroundColor Yellow
& $ensureScript
