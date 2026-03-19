# Fix Visible Scheduled Tasks - Mar 16, 2026
# Run as Administrator to add -WindowStyle Hidden to tasks that show PowerShell windows.
# Usage: Right-click PowerShell -> Run as Administrator -> .\fix-visible-scheduled-tasks.ps1

$ErrorActionPreference = "Stop"
$mas     = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts"
$website = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\scripts"

$updates = @(
    @{
        TaskName = "Mycosoft-CursorChatBackup"
        Script   = "$mas\cursor-chat-backup.ps1"
    },
    @{
        TaskName = "Mycosoft-LFS-Cleanup"
        Script   = "$mas\prevent-lfs-bloat.ps1"
    },
    @{
        TaskName = "Mycosoft-DevServerWatchdog"
        Script   = "$website\dev-server-watchdog.ps1"
    }
)

Write-Host "`nFix Visible Scheduled Tasks - will update these to run hidden:" -ForegroundColor Cyan
foreach ($u in $updates) { Write-Host "  - $($u.TaskName)" }
Write-Host ""

foreach ($u in $updates) {
    try {
        $exists = Get-ScheduledTask -TaskName $u.TaskName -ErrorAction SilentlyContinue
        if (-not $exists) {
            $hint = if ($u.TaskName -eq "Mycosoft-DevServerWatchdog") {
                " Run WEBSITE\website\scripts\register-dev-watchdog.ps1 once to create it, then run this fix again."
            } else { " Register the task first if needed, then run this fix again." }
            Write-Host "[SKIP] $($u.TaskName) - task does not exist.$hint" -ForegroundColor Yellow
            continue
        }
        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$($u.Script)`""
        Set-ScheduledTask -TaskName $u.TaskName -Action $action -ErrorAction Stop
        Write-Host "[OK] Updated $($u.TaskName) -> now runs hidden" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $($u.TaskName): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nDone. Updated tasks will run hidden (no 30s watchdog or other PowerShell pop-ups)." -ForegroundColor Cyan
