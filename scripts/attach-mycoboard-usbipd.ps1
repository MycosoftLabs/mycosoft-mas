# Attach MycoBoard (ESP32-S3 USB Serial) into WSL2 for Docker access.
#
# This enables Linux containers to access the board as /dev/ttyACM0.
#
# Requirements:
# - Docker Desktop using WSL2 backend
# - usbipd-win installed (winget install dorssel.usbipd-win)
#
# Notes:
# - The MycoBoard shows up as VID:PID 303A:1001 on many ESP32-S3 boards.
# - This script is best-effort and will not fail your startup if USB isn’t present.

$ErrorActionPreference = "Continue"

$usbipdExe = "C:\Program Files\usbipd-win\usbipd.exe"
if (-not (Test-Path $usbipdExe)) {
  Write-Host "usbipd-win not found at $usbipdExe (skipping USB attach)" -ForegroundColor Yellow
  exit 0
}

Write-Host "Looking for MycoBoard USB device (VID:PID 303A:1001)..." -ForegroundColor Cyan
$list = & $usbipdExe list 2>$null
if (-not $list) {
  Write-Host "usbipd list failed (skipping USB attach)" -ForegroundColor Yellow
  exit 0
}

# Find BUSID for Espressif USB serial
$busId = $null
foreach ($line in $list -split "`r?`n") {
  if ($line -match "303a:1001") {
    # Example: "13-3   303a:1001  USB Serial Device (COM5), ..."
    $busId = ($line -split "\s+")[0]
    break
  }
}

if (-not $busId) {
  Write-Host "MycoBoard not detected by usbipd (skipping USB attach)" -ForegroundColor Yellow
  exit 0
}

Write-Host "Found MycoBoard BUSID: $busId" -ForegroundColor Green

# Share (bind) the device (may require admin, but if already shared this is OK)
& $usbipdExe bind --busid $busId 2>$null | Out-Null

# Attach to WSL (Docker Desktop distro will be auto-selected)
& $usbipdExe attach --wsl --busid $busId 2>$null | Out-Null

# Ensure the cdc_acm driver is loaded so /dev/ttyACM0 appears.
try {
  wsl -d docker-desktop -e sh -lc "command -v modprobe >/dev/null 2>&1 && modprobe cdc_acm || true; ls -l /dev/ttyACM0 2>/dev/null || true" | Out-Null
} catch {
  # Ignore; Docker Desktop WSL may not be ready yet.
}

Write-Host "USB attach attempt complete." -ForegroundColor Green



