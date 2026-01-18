# Move app directory to deprecated folder
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline
Write-Host ("=" * 79)
Write-Host "MOVING app/ DIRECTORY TO DEPRECATED FOLDER"
Write-Host ("=" * 80)
Write-Host ""

$sourcePath = Join-Path $PSScriptRoot "..\app"
$destPath = Join-Path $PSScriptRoot "..\_deprecated_mas_website\app"

if (-not (Test-Path $sourcePath)) {
    Write-Host "[SKIP] app/ directory does not exist. Already moved?" -ForegroundColor Yellow
    exit 0
}

Write-Host "[STEP 1] Removing read-only attributes..." -ForegroundColor Cyan
Get-ChildItem -Path $sourcePath -Recurse -Force | ForEach-Object {
    if ($_.Attributes -match "ReadOnly") {
        $_.Attributes = $_.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
    }
}

Write-Host "[STEP 2] Creating destination directory..." -ForegroundColor Cyan
$destParent = Split-Path $destPath -Parent
if (-not (Test-Path $destParent)) {
    New-Item -ItemType Directory -Path $destParent -Force | Out-Null
}

if (Test-Path $destPath) {
    Write-Host "[WARNING] Destination already exists. Removing..." -ForegroundColor Yellow
    Remove-Item -Path $destPath -Recurse -Force
}

Write-Host "[STEP 3] Moving app/ directory..." -ForegroundColor Cyan
try {
    Move-Item -Path $sourcePath -Destination $destPath -Force
    Write-Host "[OK] Successfully moved app/ to _deprecated_mas_website/app/" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to move: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running PowerShell as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[VERIFY] Checking if app/ still exists..." -ForegroundColor Cyan
if (Test-Path $sourcePath) {
    Write-Host "[WARNING] app/ still exists. Manual intervention required." -ForegroundColor Yellow
} else {
    Write-Host "[OK] app/ successfully moved. No longer exists in root." -ForegroundColor Green
}

Write-Host ""
Write-Host ("=" * 80)
Write-Host "COMPLETE"
Write-Host ("=" * 80)
