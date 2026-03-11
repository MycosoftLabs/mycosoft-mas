# Claude Desktop Schedule Backup (Mar 3, 2026)
# Run BEFORE uninstalling Claude Desktop to preserve all Cowork scheduled tasks.
# Schedules live in: AppData\Claude\local-agent-mode-sessions and Documents\Claude\Scheduled

$ErrorActionPreference = "Stop"
$backupRoot = "C:\Users\admin2\Desktop\ClaudeDesktopBackup_$(Get-Date -Format 'yyyyMMdd_HHmm')"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

Write-Host "Backing up Claude Desktop schedules to: $backupRoot" -ForegroundColor Cyan

# 1. scheduled-tasks.json (definitions, cron, enabled, permissions)
# Copy only schedule data to avoid long-path/broken-symlink errors in full folder copy
$lamPath = "$env:APPDATA\Claude\local-agent-mode-sessions"
$schedJson = Get-ChildItem -Path $lamPath -Recurse -Filter "scheduled-tasks.json" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($schedJson) {
    $destDir = Join-Path $backupRoot "scheduled-tasks"
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    Copy-Item -Path $schedJson.FullName -Destination (Join-Path $destDir "scheduled-tasks.json") -Force
    # Preserve relative path for restore (account\org)
    $relPath = $schedJson.FullName -replace [regex]::Escape("$lamPath\"), ""
    $relPath | Set-Content (Join-Path $destDir "original-path.txt") -Force
    Write-Host "  [OK] scheduled-tasks.json" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] scheduled-tasks.json not found" -ForegroundColor Yellow
}

# 2. Documents\Claude\Scheduled (SKILL.md files for each task)
$scheduledPath = "$env:USERPROFILE\Documents\Claude\Scheduled"
if (Test-Path $scheduledPath) {
    $dest = Join-Path $backupRoot "Documents_Claude_Scheduled"
    Copy-Item -Path $scheduledPath -Destination $dest -Recurse -Force
    Write-Host "  [OK] Documents\Claude\Scheduled (SKILL.md files)" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] Documents\Claude\Scheduled not found" -ForegroundColor Yellow
}

# 3. Main config (coworkScheduledTasksEnabled, ccdScheduledTasksEnabled)
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
if (Test-Path $configPath) {
    Copy-Item -Path $configPath -Destination (Join-Path $backupRoot "claude_desktop_config.json") -Force
    Write-Host "  [OK] claude_desktop_config.json" -ForegroundColor Green
}

# 4. config.json (OAuth, app prefs)
$appConfig = "$env:APPDATA\Claude\config.json"
if (Test-Path $appConfig) {
    Copy-Item -Path $appConfig -Destination (Join-Path $backupRoot "config.json") -Force
    Write-Host "  [OK] config.json" -ForegroundColor Green
}

# 5. claude-code-sessions (CCD scheduled tasks)
$ccdPath = "$env:APPDATA\Claude\claude-code-sessions"
if (Test-Path $ccdPath) {
    Copy-Item -Path $ccdPath -Destination (Join-Path $backupRoot "claude-code-sessions") -Recurse -Force
    Write-Host "  [OK] claude-code-sessions" -ForegroundColor Green
}

Write-Host "`nBackup complete. Keep this folder safe until after reinstall.`n" -ForegroundColor Cyan
Write-Host "Next: Uninstall Claude Desktop, reinstall, log in, then run:" -ForegroundColor White
Write-Host "  .\scripts\claude-desktop-schedule-restore.ps1 -BackupPath '$backupRoot'" -ForegroundColor Yellow
