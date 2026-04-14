#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  One-shot bootstrap for Windows 11 Legion GPU workstations (4080A / 4080B).
  Run in PowerShell **As Administrator** on each machine via Chrome Remote Desktop.

.DESCRIPTION
  - Disables sleep on AC (stays on for remote work)
  - Installs/enables OpenSSH Server + firewall TCP 22
  - Ensures the login user can use SSH (password required — blank passwords block SSH)
  - Installs/updates: winget packages, WSL2 + Ubuntu 22.04, Docker Desktop
  - NVIDIA: installs GeForce Experience via winget (use it or nvidia.com to pull latest 4080 driver)

.PARAMETER Role
  Voice = PersonaPlex/Moshi/Nemotron host. Earth2 = Earth-2 stack host. (Tagging only — set static IP in UniFi.)

.EXAMPLE
  Set-ExecutionPolicy Bypass -Scope Process -Force
  .\Bootstrap-Legion-GPU.ps1 -Role Voice
#>
param(
    [ValidateSet('Voice', 'Earth2')]
    [string]$Role = 'Voice',
    [string]$TagFile = "$env:Public\mycosoft-gpu-role.txt"
)

$ErrorActionPreference = 'Stop'
function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }

Write-Step "Mycosoft Legion GPU bootstrap ($Role) — $(Get-Date -Format o)"

# --- Stay on when plugged in ---
Write-Step "Power: disable sleep/hibernate on AC"
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 30

# --- OpenSSH Server ---
Write-Step "OpenSSH Server"
$cap = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*' | Select-Object -First 1
if ($cap -and $cap.State -ne 'Installed') {
    Add-WindowsCapability -Online -Name $cap.Name
}
Start-Service sshd -ErrorAction SilentlyContinue
Set-Service -Name sshd -StartupType Automatic
Get-Service sshd | Format-List Status, StartType

# sshd_config: allow pubkey + password until keys are deployed
$sshd = "$env:ProgramData\ssh\sshd_config"
if (Test-Path $sshd) {
    $c = Get-Content $sshd -Raw
    if ($c -notmatch 'PubkeyAuthentication\s+yes') {
        Add-Content $sshd "`nPubkeyAuthentication yes`nPasswordAuthentication yes`n"
    }
}
Restart-Service sshd -Force

# Firewall
Write-Step "Firewall rule TCP 22"
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP-Mycosoft' -DisplayName 'OpenSSH Server (SSH) Mycosoft' `
    -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -ErrorAction SilentlyContinue | Out-Null

# --- User password (required for SSH password auth on Windows) ---
Write-Step "Account password for SSH"
Write-Host "Windows refuses SSH password login for accounts with a BLANK password." -ForegroundColor Yellow
Write-Host "Set a strong password for the account you use to SSH ($env:USERNAME)." -ForegroundColor Yellow
$sec = Read-Host "Enter NEW password for '$env:USERNAME' (will not echo)" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
)
try {
    net user $env:USERNAME $plain 2>&1 | Out-Null
    Write-Host "Password updated for local account $env:USERNAME" -ForegroundColor Green
} catch {
    Write-Warning "If this PC uses a Microsoft account, set the Windows password under Settings → Accounts → Sign-in options (required for SSH password auth)."
}

# Tag role (UniFi static IP is configured separately)
Set-Content -Path $TagFile -Value "Mycosoft GPU Role=$Role`nHost=$env:COMPUTERNAME`nDate=$(Get-Date -Format o)"

# --- winget ---
Write-Step "winget (App Installer)"
$winget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $winget) {
    Write-Host "Installing App Installer / winget from Microsoft Store may be required." -ForegroundColor Yellow
} else {
    winget source update
    winget upgrade --all --accept-package-agreements --accept-source-agreements --include-unknown
}

# Common dev tools (idempotent)
$pkgs = @(
    @{ Id = 'Git.Git'; Name = 'Git' },
    @{ Id = 'Google.Chrome'; Name = 'Chrome' }
)
foreach ($p in $pkgs) {
    Write-Step "winget install $($p.Name)"
    winget install -e --id $p.Id --accept-package-agreements --accept-source-agreements --silent 2>$null
}

# NVIDIA GeForce Experience (pulls / manages Game Ready drivers for RTX 4080)
Write-Step "NVIDIA GeForce Experience (then open it to install latest 4080 driver)"
winget install -e --id Nvidia.GeForceExperience --accept-package-agreements --accept-source-agreements --silent 2>$null

# --- WSL2 + Ubuntu ---
Write-Step "WSL2"
wsl --update 2>$null
wsl --set-default-version 2 2>$null
$dist = wsl -l -v 2>$null | Out-String
if ($dist -notmatch 'Ubuntu') {
    Write-Host "Installing Ubuntu (WSL; first run may require reboot)..." -ForegroundColor Yellow
    wsl --install -d Ubuntu -n
    Write-Host "`nIf the installer asked for a REBOOT: reboot this PC, log back in, run this script again (it is safe)." -ForegroundColor Yellow
} else {
    Write-Host "WSL distro already present.`n$dist" -ForegroundColor Green
}

# --- Docker Desktop ---
Write-Step "Docker Desktop"
winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements 2>$null

Write-Step "Done local bootstrap"
Write-Host @"

Next (manual once per machine):
1) Reboot if WSL asked for it; after reboot, open 'Ubuntu' from Start and finish UNIX user setup.
2) Open NVIDIA GeForce Experience → Drivers → install latest for RTX 4080.
3) Open Docker Desktop → finish wizard → Settings → Use WSL 2 → enable your Ubuntu distro.

Then from your DEV PC on the LAN (same Dream Machine network), run:
  scripts/gpu-node/windows/DevPC-InstallSSHKeysAndVerify.ps1

Optional first (Windows + large drive): canonical data folders + env vars
  cd scripts\gpu-node\windows
  .\Initialize-MycosoftDataLayout.ps1 -Role Earth2   # or Voice — see docs/STORAGE_LAYOUT_LEGION_GPU_APR15_2026.md

After Ubuntu WSL works and nvidia-smi works inside WSL:
  cd scripts\gpu-node\windows
  .\Invoke-WSLGPUNodeSetup.ps1 -Role Earth2   # on 4080A
  .\Invoke-WSLGPUNodeSetup.ps1 -Role Voice    # on 4080B
  See docs/WSL_LEGION_GPU_NODES_APR15_2026.md

"@ -ForegroundColor Green
