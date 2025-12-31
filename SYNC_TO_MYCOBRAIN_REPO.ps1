# Sync MycoBrain Firmware to mycobrain Repository
# This script copies all firmware files from mycosoft-mas to mycobrain repo

$ErrorActionPreference = "Stop"

Write-Host "=== MycoBrain Repository Sync Script ===" -ForegroundColor Cyan
Write-Host ""

# Check if mycobrain repo exists
$mycobrainPath = "..\mycobrain"
if (-not (Test-Path $mycobrainPath)) {
    Write-Host "mycobrain repository not found at: $mycobrainPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Would you like to clone it? (y/n)" -ForegroundColor Yellow
    $clone = Read-Host
    if ($clone -eq "y" -or $clone -eq "Y") {
        Write-Host "Cloning mycobrain repository..." -ForegroundColor Cyan
        Set-Location ..
        git clone https://github.com/MycosoftLabs/mycobrain.git
        Set-Location mycosoft-mas
        $mycobrainPath = "..\mycobrain"
    } else {
        Write-Host "Please clone the repository manually:" -ForegroundColor Yellow
        Write-Host "  cd .." -ForegroundColor White
        Write-Host "  git clone https://github.com/MycosoftLabs/mycobrain.git" -ForegroundColor White
        Write-Host "  cd mycosoft-mas" -ForegroundColor White
        exit 1
    }
}

if (-not (Test-Path $mycobrainPath)) {
    Write-Host "ERROR: mycobrain repository still not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Found mycobrain repository at: $mycobrainPath" -ForegroundColor Green
Write-Host ""

# Create directories if they don't exist
Write-Host "Creating directory structure..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$mycobrainPath\firmware\MycoBrain_SideA" | Out-Null
New-Item -ItemType Directory -Force -Path "$mycobrainPath\firmware\MycoBrain_SideB" | Out-Null
New-Item -ItemType Directory -Force -Path "$mycobrainPath\firmware\MycoBrain_ScienceComms" | Out-Null
New-Item -ItemType Directory -Force -Path "$mycobrainPath\docs" | Out-Null

# Copy Side-A firmware
Write-Host "Copying Side-A firmware..." -ForegroundColor Cyan
Copy-Item -Path "firmware\MycoBrain_SideA\MycoBrain_SideA_Production.ino" -Destination "$mycobrainPath\firmware\MycoBrain_SideA\" -Force
Copy-Item -Path "firmware\MycoBrain_SideA\README.md" -Destination "$mycobrainPath\firmware\MycoBrain_SideA\" -Force
if (Test-Path "firmware\MycoBrain_SideA\platformio.ini") {
    Copy-Item -Path "firmware\MycoBrain_SideA\platformio.ini" -Destination "$mycobrainPath\firmware\MycoBrain_SideA\" -Force
}

# Copy Side-B firmware
Write-Host "Copying Side-B firmware..." -ForegroundColor Cyan
Copy-Item -Path "firmware\MycoBrain_SideB\MycoBrain_SideB.ino" -Destination "$mycobrainPath\firmware\MycoBrain_SideB\" -Force
Copy-Item -Path "firmware\MycoBrain_SideB\README.md" -Destination "$mycobrainPath\firmware\MycoBrain_SideB\" -Force
if (Test-Path "firmware\MycoBrain_SideB\platformio.ini") {
    Copy-Item -Path "firmware\MycoBrain_SideB\platformio.ini" -Destination "$mycobrainPath\firmware\MycoBrain_SideB\" -Force
}

# Copy ScienceComms firmware (entire directory)
Write-Host "Copying ScienceComms firmware..." -ForegroundColor Cyan
if (Test-Path "firmware\MycoBrain_ScienceComms") {
    Copy-Item -Path "firmware\MycoBrain_ScienceComms\*" -Destination "$mycobrainPath\firmware\MycoBrain_ScienceComms\" -Recurse -Force
}

# Copy main firmware README
Write-Host "Copying main firmware README..." -ForegroundColor Cyan
Copy-Item -Path "firmware\README.md" -Destination "$mycobrainPath\firmware\README.md" -Force

# Copy documentation
Write-Host "Copying documentation..." -ForegroundColor Cyan
Copy-Item -Path "docs\firmware\MYCOBRAIN_PRODUCTION_FIRMWARE.md" -Destination "$mycobrainPath\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "docs\firmware\UPGRADE_CHECKLIST.md" -Destination "$mycobrainPath\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "docs\firmware\CRITICAL_FIXES_SUMMARY.md" -Destination "$mycobrainPath\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "docs\firmware\WEBSITE_INTEGRATION_UPDATES.md" -Destination "$mycobrainPath\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "docs\firmware\WEBSITE_INTEGRATION_CORRECTIONS.md" -Destination "$mycobrainPath\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "docs\firmware\MYCOBRAIN_REPO_SYNC.md" -Destination "$mycobrainPath\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "docs\firmware\COMPLETE_UPGRADE_SUMMARY.md" -Destination "$mycobrainPath\docs\" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Files Copied Successfully ===" -ForegroundColor Green
Write-Host ""

# Show what was copied
Write-Host "Files copied to mycobrain repository:" -ForegroundColor Cyan
Write-Host "  - firmware/MycoBrain_SideA/MycoBrain_SideA_Production.ino" -ForegroundColor White
Write-Host "  - firmware/MycoBrain_SideA/README.md" -ForegroundColor White
Write-Host "  - firmware/MycoBrain_SideB/MycoBrain_SideB.ino" -ForegroundColor White
Write-Host "  - firmware/MycoBrain_SideB/README.md" -ForegroundColor White
Write-Host "  - firmware/MycoBrain_ScienceComms/ (entire directory)" -ForegroundColor White
Write-Host "  - firmware/README.md" -ForegroundColor White
Write-Host "  - docs/*.md (all documentation files)" -ForegroundColor White
Write-Host ""

# Ask if user wants to commit and push
Write-Host "Would you like to commit and push to GitHub? (y/n)" -ForegroundColor Yellow
$commit = Read-Host

if ($commit -eq "y" -or $commit -eq "Y") {
    Write-Host ""
    Write-Host "Committing changes..." -ForegroundColor Cyan
    Set-Location $mycobrainPath
    
    git add .
    git status --short
    
    Write-Host ""
    Write-Host "Commit message:" -ForegroundColor Yellow
    $commitMsg = @"
Update firmware to production version 1.0.0

- Fixed analog pin mappings (GPIO6/7/10/11, was incorrectly GPIO34/35/36/39)
- Added machine mode support with NDJSON output
- Added plaintext command support (mode machine, dbg off, fmt json, scan)
- Added NeoPixel control (GPIO15, SK6805)
- Added buzzer control (GPIO16) with pattern support
- Updated all README files with verified pin configurations
- Complete documentation package included
- All critical fixes applied and verified
"@
    
    Write-Host $commitMsg -ForegroundColor White
    Write-Host ""
    Write-Host "Proceed with commit? (y/n)" -ForegroundColor Yellow
    $proceed = Read-Host
    
    if ($proceed -eq "y" -or $proceed -eq "Y") {
        git commit -m $commitMsg
        Write-Host ""
        Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
        git push origin main
        Write-Host ""
        Write-Host "=== Successfully pushed to mycobrain repository! ===" -ForegroundColor Green
    } else {
        Write-Host "Commit cancelled. Files are ready but not committed." -ForegroundColor Yellow
    }
    
    Set-Location ..\mycosoft-mas
} else {
    Write-Host ""
    Write-Host "Files copied but not committed. To commit manually:" -ForegroundColor Yellow
    Write-Host "  cd ..\mycobrain" -ForegroundColor White
    Write-Host "  git add ." -ForegroundColor White
    Write-Host "  git commit -m 'Update firmware to production v1.0.0'" -ForegroundColor White
    Write-Host "  git push origin main" -ForegroundColor White
}

Write-Host ""
Write-Host "=== Sync Complete ===" -ForegroundColor Green

