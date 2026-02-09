# Backup Cursor Chat History - Feb 6, 2026
# Backs up workspaceStorage (chat DBs) to a safe location so chats are never lost again.
# Schedule this daily: 
#   schtasks /create /tn "Mycosoft-Cursor-Chat-Backup" /tr "powershell -ExecutionPolicy Bypass -File C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\backup-cursor-chats.ps1" /sc daily /st 12:00
#
# Manual run: .\backup-cursor-chats.ps1

$ErrorActionPreference = 'SilentlyContinue'

$source = "$env:APPDATA\Cursor\User\workspaceStorage"
$backupRoot = "E:\CursorBackups"  # E: drive has 1.8 TB free
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupDir = Join-Path $backupRoot $timestamp
$maxBackups = 30  # Keep last 30 days

if (-not (Test-Path $source)) {
    Write-Host "Source not found: $source"
    exit 1
}

# Create backup dir
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Copy workspaceStorage (chat DBs)
Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] Backing up Cursor chats to $backupDir"
Copy-Item -LiteralPath $source -Destination $backupDir -Recurse -Force -ErrorAction SilentlyContinue

# Also backup settings
$settingsSource = "$env:APPDATA\Cursor\User\settings.json"
if (Test-Path $settingsSource) {
    Copy-Item $settingsSource -Destination $backupDir -Force
}
$globalState = "$env:APPDATA\Cursor\User\globalStorage"
if (Test-Path $globalState) {
    Copy-Item -LiteralPath $globalState -Destination $backupDir -Recurse -Force -ErrorAction SilentlyContinue
}

# Size of backup
$size = (Get-ChildItem $backupDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$mb = [math]::Round($size / 1MB, 1)
Write-Host "Backup complete: $mb MB -> $backupDir"

# Prune old backups (keep last N)
$allBackups = Get-ChildItem -LiteralPath $backupRoot -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
if ($allBackups.Count -gt $maxBackups) {
    $toDelete = $allBackups | Select-Object -Skip $maxBackups
    foreach ($old in $toDelete) {
        Remove-Item $old.FullName -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Pruned old backup: $($old.Name)"
    }
}

Write-Host "Done. $($allBackups.Count) backups in $backupRoot"
