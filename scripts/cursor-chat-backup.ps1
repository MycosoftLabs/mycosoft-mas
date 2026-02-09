# Cursor Chat & Agent History Daily Backup (Feb 08, 2026)
#
# Backs up ALL Cursor chat history, agent data, plans, and workspace state.
# Runs nightly at midnight via scheduled task. Keeps 30 days of local backups.
#
# What gets backed up:
#   - ai-code-tracking.db (all chats, ~130MB)
#   - globalStorage/state.vscdb (workspace state, settings, ~180MB)
#   - workspaceStorage/*/state.vscdb (per-project state)
#   - .cursor/agents/ (agent definitions)
#   - .cursor/plans/ (all Cursor plans)
#   - .cursor/mcp.json (MCP server config)
#   - .cursor/ide_state.json (IDE state)
#   - .cursor/skills/ and .cursor/skills-cursor/ (skills)
#
# Usage:
#   .\scripts\cursor-chat-backup.ps1              # Run backup now
#   .\scripts\cursor-chat-backup.ps1 -Schedule    # Install daily midnight task
#   .\scripts\cursor-chat-backup.ps1 -Unschedule  # Remove scheduled task
#   .\scripts\cursor-chat-backup.ps1 -List        # List existing backups
#   .\scripts\cursor-chat-backup.ps1 -Cleanup     # Remove backups older than 30 days

param(
    [switch]$Schedule,
    [switch]$Unschedule,
    [switch]$List,
    [switch]$Cleanup,
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Continue"

# ── Paths ────────────────────────────────────────────────────────────────────

$CursorHome = "C:\Users\admin2\.cursor"
$CursorAppData = "C:\Users\admin2\AppData\Roaming\Cursor"
$BackupRoot = "C:\Users\admin2\Desktop\MYCOSOFT\BACKUPS\cursor-chats"
$TaskName = "Mycosoft-CursorChatBackup"
$LogFile = Join-Path $BackupRoot "backup.log"

# Sources to back up
$BackupSources = @(
    @{
        Name = "Chat Database"
        Source = "$CursorHome\ai-tracking\ai-code-tracking.db"
        Dest = "ai-tracking"
        Type = "file"
        Critical = $true
    },
    @{
        Name = "Chat DB Journal"
        Source = "$CursorHome\ai-tracking\ai-code-tracking.db-journal"
        Dest = "ai-tracking"
        Type = "file"
        Critical = $false
    },
    @{
        Name = "Global State DB"
        Source = "$CursorAppData\User\globalStorage\state.vscdb"
        Dest = "globalStorage"
        Type = "file"
        Critical = $true
    },
    @{
        Name = "Global State WAL"
        Source = "$CursorAppData\User\globalStorage\state.vscdb-wal"
        Dest = "globalStorage"
        Type = "file"
        Critical = $false
    },
    @{
        Name = "Workspace Storage"
        Source = "$CursorAppData\User\workspaceStorage"
        Dest = "workspaceStorage"
        Type = "folder"
        Critical = $true
    },
    @{
        Name = "Agent Definitions"
        Source = "$CursorHome\agents"
        Dest = "agents"
        Type = "folder"
        Critical = $true
    },
    @{
        Name = "Cursor Plans"
        Source = "$CursorHome\plans"
        Dest = "plans"
        Type = "folder"
        Critical = $true
    },
    @{
        Name = "MCP Config"
        Source = "$CursorHome\mcp.json"
        Dest = "config"
        Type = "file"
        Critical = $true
    },
    @{
        Name = "IDE State"
        Source = "$CursorHome\ide_state.json"
        Dest = "config"
        Type = "file"
        Critical = $false
    },
    @{
        Name = "Skills"
        Source = "$CursorHome\skills"
        Dest = "skills"
        Type = "folder"
        Critical = $false
    },
    @{
        Name = "Skills (Cursor)"
        Source = "$CursorHome\skills-cursor"
        Dest = "skills-cursor"
        Type = "folder"
        Critical = $false
    },
    @{
        Name = "Cursor Rules"
        Source = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.cursor\rules"
        Dest = "cursor-rules"
        Type = "folder"
        Critical = $true
    },
    @{
        Name = "User Settings"
        Source = "$CursorAppData\User\settings.json"
        Dest = "config"
        Type = "file"
        Critical = $false
    },
    @{
        Name = "Keybindings"
        Source = "$CursorAppData\User\keybindings.json"
        Dest = "config"
        Type = "file"
        Critical = $false
    }
)

# ── Functions ────────────────────────────────────────────────────────────────

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$timestamp] [$Level] $Message"
    Write-Host $entry
    if (Test-Path (Split-Path $LogFile -Parent)) {
        Add-Content -Path $LogFile -Value $entry -ErrorAction SilentlyContinue
    }
}

function Run-Backup {
    $datestamp = Get-Date -Format "yyyy-MM-dd"
    $timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
    $backupDir = Join-Path $BackupRoot $datestamp
    $backupSubDir = Join-Path $backupDir $timestamp

    # Create backup directory
    New-Item -ItemType Directory -Path $backupSubDir -Force | Out-Null

    Write-Log "============================================="
    Write-Log "CURSOR CHAT BACKUP STARTING"
    Write-Log "Backup to: $backupSubDir"
    Write-Log "============================================="

    $totalSize = 0
    $successCount = 0
    $failCount = 0

    foreach ($src in $BackupSources) {
        $srcPath = $src.Source
        $destPath = Join-Path $backupSubDir $src.Dest

        if (-not (Test-Path $srcPath)) {
            if ($src.Critical) {
                Write-Log "MISSING (critical): $($src.Name) - $srcPath" "WARN"
            }
            continue
        }

        New-Item -ItemType Directory -Path $destPath -Force | Out-Null

        try {
            if ($src.Type -eq "file") {
                $fileName = Split-Path $srcPath -Leaf
                $destFile = Join-Path $destPath $fileName
                Copy-Item -Path $srcPath -Destination $destFile -Force
                $fileSize = (Get-Item $destFile).Length
                $totalSize += $fileSize
                $sizeMB = [math]::Round($fileSize / 1MB, 1)
                Write-Log "OK: $($src.Name) ($sizeMB MB)"
                $successCount++
            }
            elseif ($src.Type -eq "folder") {
                # Copy folder contents (only .db, .vscdb, .json, .md, .mdc files to save space)
                $extensions = @("*.db", "*.vscdb", "*.vscdb-wal", "*.vscdb-shm", "*.json", "*.md", "*.mdc", "*.plan.md")
                $copiedFiles = 0
                $folderSize = 0

                foreach ($ext in $extensions) {
                    $files = Get-ChildItem -Path $srcPath -Filter $ext -Recurse -ErrorAction SilentlyContinue
                    foreach ($file in $files) {
                        $relativePath = $file.FullName.Substring($srcPath.Length)
                        $destFile = Join-Path $destPath $relativePath
                        $destFileDir = Split-Path $destFile -Parent
                        New-Item -ItemType Directory -Path $destFileDir -Force | Out-Null
                        Copy-Item -Path $file.FullName -Destination $destFile -Force
                        $folderSize += $file.Length
                        $copiedFiles++
                    }
                }

                $totalSize += $folderSize
                $sizeMB = [math]::Round($folderSize / 1MB, 1)
                Write-Log "OK: $($src.Name) ($copiedFiles files, $sizeMB MB)"
                $successCount++
            }
        }
        catch {
            Write-Log "FAILED: $($src.Name) - $_" "ERROR"
            $failCount++
        }
    }

    # Write backup manifest
    $manifest = @{
        timestamp  = (Get-Date -Format "o")
        date       = $datestamp
        machine    = $env:COMPUTERNAME
        user       = $env:USERNAME
        totalSizeMB = [math]::Round($totalSize / 1MB, 1)
        sources    = $successCount
        failures   = $failCount
        backupPath = $backupSubDir
    } | ConvertTo-Json -Depth 3

    $manifestPath = Join-Path $backupSubDir "backup_manifest.json"
    Set-Content -Path $manifestPath -Value $manifest -Encoding UTF8

    # Summary
    $totalMB = [math]::Round($totalSize / 1MB, 1)
    Write-Log "============================================="
    Write-Log "BACKUP COMPLETE"
    Write-Log "  Items backed up: $successCount"
    Write-Log "  Failures:        $failCount"
    Write-Log "  Total size:      $totalMB MB"
    Write-Log "  Location:        $backupSubDir"
    Write-Log "============================================="

    # Cleanup old backups
    Cleanup-Old -Silent
}

function Cleanup-Old {
    param([switch]$Silent)

    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    $removed = 0

    if (Test-Path $BackupRoot) {
        Get-ChildItem $BackupRoot -Directory | Where-Object {
            $_.Name -match "^\d{4}-\d{2}-\d{2}$" -and $_.LastWriteTime -lt $cutoff
        } | ForEach-Object {
            Remove-Item $_.FullName -Recurse -Force
            $removed++
            if (-not $Silent) { Write-Log "Removed old backup: $($_.Name)" }
        }
    }

    if ($removed -gt 0) {
        Write-Log "Cleaned up $removed backup(s) older than $RetentionDays days"
    }
}

function List-Backups {
    Write-Host ""
    Write-Host "CURSOR CHAT BACKUPS" -ForegroundColor Cyan
    Write-Host "Location: $BackupRoot"
    Write-Host ""

    if (-not (Test-Path $BackupRoot)) {
        Write-Host "No backups found." -ForegroundColor Yellow
        return
    }

    $dirs = Get-ChildItem $BackupRoot -Directory | Where-Object { $_.Name -match "^\d{4}-\d{2}-\d{2}$" } | Sort-Object Name -Descending
    if ($dirs.Count -eq 0) {
        Write-Host "No backups found." -ForegroundColor Yellow
        return
    }

    foreach ($day in $dirs) {
        $subBackups = Get-ChildItem $day.FullName -Directory
        $totalSize = (Get-ChildItem $day.FullName -Recurse -File | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($totalSize / 1MB, 1)
        Write-Host "  $($day.Name)  ($($subBackups.Count) backup(s), $sizeMB MB)" -ForegroundColor Green
    }

    $totalAll = (Get-ChildItem $BackupRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $totalGB = [math]::Round($totalAll / 1GB, 2)
    Write-Host ""
    Write-Host "  Total: $($dirs.Count) days, $totalGB GB" -ForegroundColor Cyan
}

function Install-Schedule {
    $scriptPath = $MyInvocation.ScriptName
    if (-not $scriptPath) { $scriptPath = $PSCommandPath }

    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

    $trigger = New-ScheduledTaskTrigger -Daily -At "12:00AM"

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable:$false `
        -WakeToRun

    try {
        Register-ScheduledTask `
            -TaskName $TaskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Description "Daily backup of Cursor chat history, agents, and plans at midnight" `
            -Force

        Write-Host "Scheduled task '$TaskName' created." -ForegroundColor Green
        Write-Host "  Runs daily at midnight"
        Write-Host "  Backups saved to: $BackupRoot"
        Write-Host "  Retention: $RetentionDays days"
        Write-Host ""
        Write-Host "  To remove: .\scripts\cursor-chat-backup.ps1 -Unschedule"
    }
    catch {
        Write-Host "Failed to create scheduled task: $_" -ForegroundColor Red
        Write-Host "Try running PowerShell as Administrator" -ForegroundColor Yellow
    }
}

function Remove-Schedule {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "Scheduled task '$TaskName' removed." -ForegroundColor Green
    }
    catch {
        Write-Host "Task '$TaskName' not found or could not be removed." -ForegroundColor Yellow
    }
}

# ── Main ─────────────────────────────────────────────────────────────────────

if ($Schedule) {
    Install-Schedule
}
elseif ($Unschedule) {
    Remove-Schedule
}
elseif ($List) {
    List-Backups
}
elseif ($Cleanup) {
    Cleanup-Old
}
else {
    # Ensure backup root exists
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    Run-Backup
}
