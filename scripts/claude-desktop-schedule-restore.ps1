# Claude Desktop Schedule Restore (Mar 3, 2026)
# Run AFTER reinstalling Claude Desktop and logging in at least once.
# Usage: .\claude-desktop-schedule-restore.ps1 -BackupPath "C:\Users\admin2\Desktop\ClaudeDesktopBackup_20260306_1500"

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupPath)) {
    Write-Host "ERROR: Backup path not found: $BackupPath" -ForegroundColor Red
    exit 1
}

Write-Host "Restoring Claude Desktop schedules from: $BackupPath" -ForegroundColor Cyan

# Claude must be closed for a clean restore. User should close it first.
Write-Host "`nEnsure Claude Desktop is CLOSED before restoring.`n" -ForegroundColor Yellow

# 1. Restore scheduled-tasks.json
$schedBackupFile = Join-Path $BackupPath "scheduled-tasks\scheduled-tasks.json"
$lamDest = "$env:APPDATA\Claude\local-agent-mode-sessions"
if (Test-Path $schedBackupFile) {
    $targetDir = $null
    # Prefer original path if it exists (same account/org IDs after reinstall)
    $pathFile = Join-Path $BackupPath "scheduled-tasks\original-path.txt"
    if (Test-Path $pathFile) {
        $relPath = (Get-Content $pathFile -Raw).Trim()
        $candidate = Join-Path $lamDest (Split-Path $relPath -Parent)
        if (Test-Path (Split-Path $candidate -Parent)) { $targetDir = $candidate }
    }
    # Else find first account\org dir (e.g. uuid\uuid) under local-agent-mode-sessions
    if (-not $targetDir -and (Test-Path $lamDest)) {
        $accounts = Get-ChildItem -Path $lamDest -Directory -ErrorAction SilentlyContinue
        foreach ($acc in $accounts) {
            $orgs = Get-ChildItem -Path $acc.FullName -Directory -ErrorAction SilentlyContinue
            foreach ($org in $orgs) { $targetDir = $org.FullName; break }
            if ($targetDir) { break }
        }
    }
    if ($targetDir) {
        if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
        Copy-Item -Path $schedBackupFile -Destination (Join-Path $targetDir "scheduled-tasks.json") -Force
        Write-Host "  [OK] Restored scheduled-tasks.json" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] No target folder. Log into Claude once, then re-run restore." -ForegroundColor Yellow
    }
}

# 2. Restore Documents\Claude\Scheduled
$schedBackup = Join-Path $BackupPath "Documents_Claude_Scheduled"
$schedDest = "$env:USERPROFILE\Documents\Claude\Scheduled"
if (Test-Path $schedBackup) {
    if (-not (Test-Path $schedDest)) { New-Item -ItemType Directory -Path $schedDest -Force | Out-Null }
    Copy-Item -Path "$schedBackup\*" -Destination $schedDest -Recurse -Force
    Write-Host "  [OK] Restored Documents\Claude\Scheduled" -ForegroundColor Green
}

# 3. Restore claude_desktop_config.json (merge schedule flags if needed)
$configBackup = Join-Path $BackupPath "claude_desktop_config.json"
$configDest = "$env:APPDATA\Claude\claude_desktop_config.json"
if (Test-Path $configBackup) {
    $backup = Get-Content $configBackup -Raw | ConvertFrom-Json
    if (Test-Path $configDest) {
        $current = Get-Content $configDest -Raw | ConvertFrom-Json
        # Preserve schedule flags from backup
        if ($null -ne $backup.PSObject.Properties['coworkScheduledTasksEnabled']) {
            $current | Add-Member -NotePropertyName 'coworkScheduledTasksEnabled' -NotePropertyValue $backup.coworkScheduledTasksEnabled -Force
        }
        if ($null -ne $backup.PSObject.Properties['ccdScheduledTasksEnabled']) {
            $current | Add-Member -NotePropertyName 'ccdScheduledTasksEnabled' -NotePropertyValue $backup.ccdScheduledTasksEnabled -Force
        }
        $current | ConvertTo-Json -Depth 10 | Set-Content $configDest -Encoding UTF8
    } else {
        Copy-Item -Path $configBackup -Destination $configDest -Force
    }
    Write-Host "  [OK] Restored schedule flags in claude_desktop_config.json" -ForegroundColor Green
}

# 4. Optional: claude-code-sessions (CCD schedules)
$ccdBackup = Join-Path $BackupPath "claude-code-sessions"
$ccdDest = "$env:APPDATA\Claude\claude-code-sessions"
if (Test-Path $ccdBackup) {
    if (-not (Test-Path $ccdDest)) { New-Item -ItemType Directory -Path $ccdDest -Force | Out-Null }
    Copy-Item -Path "$ccdBackup\*" -Destination $ccdDest -Recurse -Force
    Write-Host "  [OK] Restored claude-code-sessions" -ForegroundColor Green
}

Write-Host "`nRestore complete. Restart Claude Desktop to pick up schedules.`n" -ForegroundColor Cyan
