# Setup Device Media Folders - Creates folder structure on NAS and local
# Run from Windows machine with access to the NAS share

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Mycosoft Device Media Folder Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Configuration
$NAS_SHARE = "\\192.168.0.105\mycosoft.com"
$NAS_ASSETS_PATH = "$NAS_SHARE\website\assets"
$LOCAL_ASSETS_PATH = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\public\assets"

# Device folder names (must match code references)
$DEVICES = @(
    "mushroom1",
    "sporebase",
    "hyphae1",
    "myconode",
    "alarm"
)

Write-Host ""
Write-Host "Creating local asset folders..." -ForegroundColor Yellow

foreach ($device in $DEVICES) {
    $localPath = Join-Path $LOCAL_ASSETS_PATH $device
    if (-not (Test-Path $localPath)) {
        New-Item -ItemType Directory -Force -Path $localPath | Out-Null
        Write-Host "  [CREATED] $localPath" -ForegroundColor Green
    } else {
        Write-Host "  [EXISTS]  $localPath" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Creating NAS asset folders..." -ForegroundColor Yellow

# Test NAS connectivity first
if (Test-Path $NAS_SHARE) {
    foreach ($device in $DEVICES) {
        $nasPath = Join-Path $NAS_ASSETS_PATH $device
        if (-not (Test-Path $nasPath)) {
            try {
                New-Item -ItemType Directory -Force -Path $nasPath | Out-Null
                Write-Host "  [CREATED] $nasPath" -ForegroundColor Green
            } catch {
                Write-Host "  [ERROR]   Failed to create $nasPath : $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  [EXISTS]  $nasPath" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "  [WARN]    NAS share not accessible: $NAS_SHARE" -ForegroundColor Yellow
    Write-Host "            Make sure you're connected to the network and have access to the share." -ForegroundColor Yellow
    Write-Host "            You can create folders manually via:" -ForegroundColor Yellow
    foreach ($device in $DEVICES) {
        Write-Host "              New-Item -ItemType Directory -Force -Path `"$NAS_ASSETS_PATH\$device`"" -ForegroundColor DarkCyan
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Device media folders are structured as:" -ForegroundColor White
Write-Host ""
Write-Host "  Local (for development):" -ForegroundColor Yellow
foreach ($device in $DEVICES) {
    Write-Host "    public/assets/$device/" -ForegroundColor White
}
Write-Host ""
Write-Host "  NAS (for production):" -ForegroundColor Yellow
foreach ($device in $DEVICES) {
    Write-Host "    \\192.168.0.105\mycosoft.com\website\assets\$device\" -ForegroundColor White
}
Write-Host ""
Write-Host "  Public URLs:" -ForegroundColor Yellow
foreach ($device in $DEVICES) {
    Write-Host "    https://sandbox.mycosoft.com/assets/$device/*" -ForegroundColor White
}
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Add media files to the appropriate device folders" -ForegroundColor White
Write-Host "  2. Run: python scripts/media/sync_website_media_paramiko.py" -ForegroundColor White
Write-Host "  3. Restart container: docker restart mycosoft-website" -ForegroundColor White
Write-Host "  4. Purge Cloudflare cache if needed" -ForegroundColor White
Write-Host ""
