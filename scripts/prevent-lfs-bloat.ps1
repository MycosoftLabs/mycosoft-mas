# Prevent LFS & Git Garbage Bloat - Feb 6, 2026
# Runs hourly via Task Scheduler to catch and kill any LFS/git garbage.
#
# ROOT CAUSE: Cursor's background git integration spawned git-lfs processes
# that downloaded temp files into .git/lfs/tmp. 1,572 failed downloads = 1.74 TB.
#
# PERMANENT FIX APPLIED:
#   - models/personaplex-7b-v1/.gitattributes: all filter=lfs rules removed
#   - .lfsconfig: fetchexclude=*, concurrenttransfers=0
#   - git config local: filter.lfs.smudge/process set to --skip, required=false
#   - git config global: all LFS filters removed
#
# This script is a SAFETY NET in case anything re-enables LFS.
#
# Usage: .\prevent-lfs-bloat.ps1
# Scheduled hourly: schtasks /create /tn "Mycosoft-LFS-Cleanup" /tr "powershell -ExecutionPolicy Bypass -File C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\prevent-lfs-bloat.ps1" /sc hourly /f

param([switch]$Verbose)

$ErrorActionPreference = 'SilentlyContinue'

$repos = @(
    "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
)

$totalFreed = 0

foreach ($repo in $repos) {
    # 1. Kill any git-lfs processes (they should never be running)
    $lfsProcs = Get-Process -Name "git-lfs" -ErrorAction SilentlyContinue
    if ($lfsProcs.Count -gt 0) {
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] WARNING: $($lfsProcs.Count) git-lfs processes found! Killing..."
        $lfsProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    }

    # 2. Clean ALL of .git/lfs (tmp, objects, cache - everything)
    $lfsDir = Join-Path $repo ".git\lfs"
    if (Test-Path $lfsDir) {
        foreach ($sub in @("tmp", "objects", "cache")) {
            $subDir = Join-Path $lfsDir $sub
            if (-not (Test-Path $subDir)) { continue }
            $files = Get-ChildItem -LiteralPath $subDir -Recurse -File -Force -ErrorAction SilentlyContinue
            $count = ($files | Measure-Object).Count
            $size = ($files | Measure-Object -Property Length -Sum).Sum
            $gb = [math]::Round($size / 1GB, 2)
            if ($count -gt 0) {
                Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] Cleaning $count LFS $sub files ($gb GB) in $repo"
                Get-ChildItem -LiteralPath $subDir -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                $totalFreed += $gb
            }
        }
    }

    # 3. Ensure LFS config is still disabled (Cursor or git operations may reset it)
    Push-Location $repo
    
    # Check .gitattributes in models dir hasn't been restored
    $modelsGitattr = Join-Path $repo "models\personaplex-7b-v1\.gitattributes"
    if (Test-Path $modelsGitattr) {
        $content = Get-Content $modelsGitattr -Raw -ErrorAction SilentlyContinue
        if ($content -match 'filter=lfs') {
            Write-Host "  WARNING: LFS filters found in models/.gitattributes! Removing..."
            Set-Content $modelsGitattr "# LFS tracking DISABLED - auto-cleaned by prevent-lfs-bloat.ps1`n"
        }
    }

    # Check git config
    $smudge = git config --local filter.lfs.smudge 2>$null
    if (-not $smudge -or $smudge -notmatch '--skip') {
        Write-Host "  Re-applying LFS skip config"
        git config --local filter.lfs.smudge "git-lfs smudge --skip -- %f"
        git config --local filter.lfs.process "git-lfs filter-process --skip"
        git config --local filter.lfs.required false
        git config --local lfs.fetchexclude "*"
        git config --local lfs.concurrenttransfers 0
    }
    Pop-Location
}

if ($totalFreed -gt 0) {
    Write-Host "Total freed: $totalFreed GB"
} elseif ($Verbose) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] All clean."
}

# Warn if drive is getting low
$drive = Get-PSDrive C
$freeGB = [math]::Round($drive.Free / 1GB, 0)
if ($freeGB -lt 500) {
    Write-Host "WARNING: C: drive only has $freeGB GB free!" -ForegroundColor Red
}
