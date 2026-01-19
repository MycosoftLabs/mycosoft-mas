<#
Mycosoft - Website Media Sync
============================

Purpose:
- Move large media (videos) outside git/docker builds.
- Sync media quickly to NAS or directly to the VM.

Usage examples:
- Sync local website public media to a NAS folder:
    powershell -ExecutionPolicy Bypass -File scripts\media\sync-website-media.ps1 `
      -Source "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\public\assets" `
      -Dest "\\MYCOSOFT-NAS\mycosoft-media\website\assets"

- Sync to VM over SSH via scp (requires OpenSSH scp + passwordless key recommended):
    powershell -ExecutionPolicy Bypass -File scripts\media\sync-website-media.ps1 `
      -Source "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\public\assets" `
      -Dest "mycosoft@192.168.0.187:/opt/mycosoft/media/website/assets"

Notes:
- For best performance on LAN, prefer NAS then mount on VM.
- This script intentionally avoids touching git/docker.
#>

param(
  [Parameter(Mandatory=$true)]
  [string]$Source,

  [Parameter(Mandatory=$true)]
  [string]$Dest
)

$ErrorActionPreference = "Stop"

function Assert-Path([string]$path, [string]$label) {
  if (-not (Test-Path $path)) { throw "$label path not found: $path" }
}

Assert-Path $Source "Source"

Write-Host "============================================================"
Write-Host " Mycosoft Website Media Sync"
Write-Host "------------------------------------------------------------"
Write-Host " Source: $Source"
Write-Host " Dest  : $Dest"
Write-Host "============================================================"

# If dest looks like scp (user@host:/path), use scp recursively.
if ($Dest -match "^[^@\\s]+@[^:\\s]+:.+") {
  $scp = Get-Command scp -ErrorAction SilentlyContinue
  if (-not $scp) { throw "scp not found. Install OpenSSH client or use NAS destination." }

  # Fast path: scp -r. (For very large trees, rclone is better.)
  Write-Host "`n[INFO] Using scp copy (recursive)."
  & scp -r "$Source" "$Dest"
  Write-Host "`n[OK] scp completed."
  exit 0
}

# If dest is UNC/local path, use robocopy for incremental, fast copy.
Write-Host "`n[INFO] Using robocopy incremental sync."
$robocopy = Get-Command robocopy -ErrorAction SilentlyContinue
if (-not $robocopy) { throw "robocopy not found (unexpected on Windows)." }

# Robocopy exit codes: 0-7 are success-ish; >= 8 is failure.
& robocopy "$Source" "$Dest" /MIR /FFT /Z /R:2 /W:2 /NP /NDL /NFL
$code = $LASTEXITCODE
if ($code -ge 8) { throw "robocopy failed with exit code $code" }

Write-Host "`n[OK] robocopy completed (exit code $code)."

