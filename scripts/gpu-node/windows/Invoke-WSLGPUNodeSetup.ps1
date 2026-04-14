#Requires -Version 5.1
<#
.SYNOPSIS
  Copy WSL GPU setup script into Ubuntu (WSL2) and run it for Earth2 or Voice role.

.DESCRIPTION
  Run on each Legion AFTER:
    - Windows NVIDIA driver installed (nvidia-smi works in PowerShell)
    - WSL2 + Ubuntu installed (see Bootstrap-Legion-GPU.ps1)
    - Ubuntu first-time user setup completed (unix username/password)

  This does NOT install bare-metal NVIDIA drivers inside Linux — WSL uses the Windows driver.

.PARAMETER Role
  Earth2 = earth2studio + Earth2 API venv on 4080A (GPU_EARTH2 host)
  Voice    = Moshi + PersonaPlex + HF tooling on 4080B (GPU_VOICE host)

.EXAMPLE
  Set-ExecutionPolicy Bypass -Scope Process -Force
  .\Invoke-WSLGPUNodeSetup.ps1 -Role Earth2
#>
param(
    [ValidateSet('Earth2', 'Voice')]
    [string]$Role = 'Voice'
)

$ErrorActionPreference = 'Stop'

$map = @{ Earth2 = 'earth2'; Voice = 'voice' }
$roleLower = $map[$Role]

Write-Host "`n=== Invoke-WSLGPUNodeSetup ($Role -> $roleLower) ===" -ForegroundColor Cyan

# wsl -l -q output can be UTF-16; avoid piping that breaks Where-Object on some hosts.
$distro = 'Ubuntu'
wsl -d $distro -e /bin/true 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "WSL distro '$distro' not found or not running. Install: wsl --install -d Ubuntu; then ubuntu.exe install --root"
}

Write-Host "Using WSL distro: $distro" -ForegroundColor Green

$wslUser = (wsl -d $distro -e whoami).Trim()
if (-not $wslUser) { throw "Could not resolve WSL username (whoami)." }

$gpuNodeDir = Split-Path (Split-Path $MyInvocation.MyCommand.Path)
$srcSh = Join-Path $gpuNodeDir "wsl\wsl-gpu-node-setup.sh"
$srcData = Join-Path $gpuNodeDir "wsl\wsl-mycosoft-data-layout.sh"
if (-not (Test-Path $srcSh)) {
    throw "Missing $srcSh - run from mycosoft-mas clone."
}

# UNC path: root uses /root; other users use /home/<user>
if ($wslUser -eq 'root') {
    $destDir = "\\wsl$\$distro\root\mycosoft-wsl-setup"
    $bashPath = "/root/mycosoft-wsl-setup/wsl-gpu-node-setup.sh"
} else {
    $destDir = "\\wsl$\$distro\home\$wslUser\mycosoft-wsl-setup"
    $bashPath = "/home/$wslUser/mycosoft-wsl-setup/wsl-gpu-node-setup.sh"
}
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
Copy-Item -Force $srcSh (Join-Path $destDir "wsl-gpu-node-setup.sh")
if (Test-Path $srcData) {
    Copy-Item -Force $srcData (Join-Path $destDir "wsl-mycosoft-data-layout.sh")
}

Write-Host "Copied scripts into WSL (mycosoft-wsl-setup)" -ForegroundColor Green
Write-Host "Running (long: PyTorch + deps download)..." -ForegroundColor Yellow

# Use ; not && so PowerShell 5.1 does not parse bash line as PS; pass one bash -lc string
$bashLine = "chmod +x '$bashPath'; exec bash '$bashPath' --role $roleLower --yes"
wsl -d $distro -e bash -lc $bashLine

Write-Host "`nDone. In WSL: source ~/mycosoft-venvs/mycosoft-$roleLower-wsl/bin/activate" -ForegroundColor Green
