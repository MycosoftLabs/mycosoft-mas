# Mycosoft Notion Docs Sync - PowerShell Launcher (Feb 08, 2026)
# Quick commands for syncing documentation to Notion
#
# Usage:
#   .\scripts\notion-sync.ps1 setup     # Interactive setup
#   .\scripts\notion-sync.ps1 sync      # Full sync all repos
#   .\scripts\notion-sync.ps1 dry-run   # Preview without changes
#   .\scripts\notion-sync.ps1 watch     # Start file watcher
#   .\scripts\notion-sync.ps1 watch-bg  # Start watcher in background
#   .\scripts\notion-sync.ps1 status    # Check watcher status
#   .\scripts\notion-sync.ps1 stop      # Stop background watcher
#   .\scripts\notion-sync.ps1 schedule  # Create Windows scheduled task

param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "sync", "dry-run", "watch", "watch-bg", "status", "stop", "schedule", "force")]
    [string]$Action = "sync",

    [string]$Repo = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonScript = Join-Path $ScriptDir "notion_docs_sync.py"
$WatcherScript = Join-Path $ScriptDir "notion_docs_watcher.py"
$PidFile = Join-Path $ProjectRoot "data\notion_watcher.pid"

function Ensure-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "Python not found. Please install Python 3.11+."
        exit 1
    }
    return $python.Source
}

function Ensure-Dependencies {
    $python = Ensure-Python
    & $python -c "import requests" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing required packages..." -ForegroundColor Yellow
        & $python -m pip install requests watchdog --quiet
    }
}

switch ($Action) {
    "setup" {
        $python = Ensure-Python
        Ensure-Dependencies
        & $python $PythonScript --setup
    }

    "sync" {
        $python = Ensure-Python
        Ensure-Dependencies
        if ($Repo) {
            & $python $PythonScript --repo $Repo
        }
        else {
            & $python $PythonScript
        }
    }

    "dry-run" {
        $python = Ensure-Python
        Ensure-Dependencies
        if ($Repo) {
            & $python $PythonScript --dry-run --repo $Repo
        }
        else {
            & $python $PythonScript --dry-run
        }
    }

    "force" {
        $python = Ensure-Python
        Ensure-Dependencies
        if ($Repo) {
            & $python $PythonScript --force --repo $Repo
        }
        else {
            & $python $PythonScript --force
        }
    }

    "watch" {
        $python = Ensure-Python
        Ensure-Dependencies
        Write-Host "Starting Notion docs watcher (Ctrl+C to stop)..." -ForegroundColor Cyan
        & $python $WatcherScript
    }

    "watch-bg" {
        $python = Ensure-Python
        Ensure-Dependencies
        Write-Host "Starting Notion docs watcher in background..." -ForegroundColor Cyan

        $proc = Start-Process -FilePath $python -ArgumentList $WatcherScript `
            -WindowStyle Hidden -PassThru
        
        # Save PID
        $dataDir = Join-Path $ProjectRoot "data"
        if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
        $proc.Id | Out-File $PidFile -Force

        Write-Host "Watcher started (PID: $($proc.Id))" -ForegroundColor Green
        Write-Host "Log: $(Join-Path $ProjectRoot 'data\notion_watcher.log')"
        Write-Host "Stop with: .\scripts\notion-sync.ps1 stop"
    }

    "status" {
        if (Test-Path $PidFile) {
            $pid = Get-Content $PidFile
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "Watcher is RUNNING (PID: $pid)" -ForegroundColor Green
                Write-Host "  Started: $($proc.StartTime)"
                Write-Host "  Memory:  $([math]::Round($proc.WorkingSet64 / 1MB, 1)) MB"
            }
            else {
                Write-Host "Watcher is NOT running (stale PID: $pid)" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "Watcher is NOT running" -ForegroundColor Yellow
        }

        # Show log tail
        $logFile = Join-Path $ProjectRoot "data\notion_watcher.log"
        if (Test-Path $logFile) {
            Write-Host "`nRecent log entries:" -ForegroundColor Cyan
            Get-Content $logFile -Tail 10
        }
    }

    "stop" {
        if (Test-Path $PidFile) {
            $pid = Get-Content $PidFile
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $pid -Force
                Write-Host "Watcher stopped (PID: $pid)" -ForegroundColor Green
            }
            else {
                Write-Host "Watcher was not running" -ForegroundColor Yellow
            }
            Remove-Item $PidFile -Force
        }
        else {
            Write-Host "No watcher PID file found" -ForegroundColor Yellow
            # Try to find and kill any running watchers
            $procs = Get-Process -Name python -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*notion_docs_watcher*" }
            if ($procs) {
                $procs | Stop-Process -Force
                Write-Host "Killed $($procs.Count) watcher process(es)" -ForegroundColor Green
            }
        }
    }

    "schedule" {
        Write-Host "Creating Windows Scheduled Task for daily Notion sync..." -ForegroundColor Cyan
        $python = Ensure-Python

        # Create scheduled task for daily sync at 3 AM
        $action = New-ScheduledTaskAction -Execute $python -Argument $PythonScript `
            -WorkingDirectory $ProjectRoot

        $trigger = New-ScheduledTaskTrigger -Daily -At 3am

        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RunOnlyIfNetworkAvailable

        try {
            Register-ScheduledTask `
                -TaskName "Mycosoft-NotionDocsSync" `
                -Action $action `
                -Trigger $trigger `
                -Settings $settings `
                -Description "Daily sync of Mycosoft docs to Notion" `
                -Force

            Write-Host "Scheduled task created: Mycosoft-NotionDocsSync" -ForegroundColor Green
            Write-Host "  Runs daily at 3:00 AM"
            Write-Host "  To remove: Unregister-ScheduledTask -TaskName 'Mycosoft-NotionDocsSync'"
        }
        catch {
            Write-Host "Failed to create scheduled task (may need admin): $_" -ForegroundColor Red
            Write-Host "Try running PowerShell as Administrator"
        }
    }
}
