# Remove Duplicate Chat Backup Task - Mar 16, 2026
# Run as Administrator. There should be only ONE chat backup:
#   - Mycosoft-CursorChatBackup (cursor-chat-backup.ps1) @ 1 AM -> C:\...\BACKUPS\cursor-chats
# This script removes the DUPLICATE:
#   - Mycosoft-Cursor-Chat-Backup (backup-cursor-chats.ps1) @ noon -> E:\CursorBackups
#
# Usage: Right-click PowerShell -> Run as Administrator, then:
#   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
#   .\scripts\remove-duplicate-backup-task.ps1

$taskName = "Mycosoft-Cursor-Chat-Backup"
$task = schtasks /query /tn $taskName 2>$null
if ($task) {
    schtasks /delete /tn $taskName /f
    if ($LASTEXITCODE -eq 0) { Write-Host "Removed duplicate task: $taskName" -ForegroundColor Green }
    else { Write-Host "Failed. Run this script as Administrator." -ForegroundColor Red; exit 1 }
} else {
    Write-Host "Task $taskName not found (already removed)." -ForegroundColor Yellow
}
