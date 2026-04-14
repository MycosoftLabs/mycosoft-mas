#Requires -Version 5.1
<#
.SYNOPSIS
  Same goals as Bootstrap-Legion-GPU.ps1, but safe over non-interactive SSH (no UAC).
  Admin-only steps run only when the session is elevated; otherwise they are skipped and logged.

  For a full install (OpenSSH service, firewall, powercfg), run Bootstrap-Legion-GPU.ps1
  in an elevated PowerShell on the machine (e.g. Chrome Remote Desktop → Run as administrator).

.PARAMETER SkipPasswordPrompt
  Do not prompt to change the Windows password (required for non-interactive SSH).
#>
param(
    [ValidateSet('Voice', 'Earth2')]
    [string]$Role = 'Voice',
    [string]$TagFile = "$env:Public\mycosoft-gpu-role.txt",
    [switch]$SkipPasswordPrompt
)

$ErrorActionPreference = 'Continue'
$LogFile = Join-Path $env:USERPROFILE "Desktop\scripts\bootstrap-ssh-session-$(Get-Date -Format yyyyMMdd-HHmmss).log"
function Log($m) {
    $line = "$(Get-Date -Format o) $m"
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
    Write-Host $line
}
function Write-Step($m) { Log "`n=== $m ===" }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
Write-Step "Mycosoft Legion GPU bootstrap SSH session ($Role) admin=$isAdmin"
Log "Log file: $LogFile"

if (-not $isAdmin) {
    Log "WARNING: Session is not elevated. Admin-only steps will be skipped."
    Log "On-box: open PowerShell as Administrator and run .\Bootstrap-Legion-GPU.ps1 -Role $Role"
}

# --- Power (admin) ---
Write-Step "Power: disable sleep on AC"
if ($isAdmin) {
    try {
        powercfg /change standby-timeout-ac 0 2>&1 | Out-Null
        powercfg /change hibernate-timeout-ac 0 2>&1 | Out-Null
        powercfg /change monitor-timeout-ac 30 2>&1 | Out-Null
        Log "powercfg: ok"
    } catch { Log "powercfg: $_" }
} else { Log "SKIP powercfg (need admin)" }

# --- OpenSSH Server (admin) ---
Write-Step "OpenSSH Server"
if ($isAdmin) {
    try {
        $cap = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*' | Select-Object -First 1
        if ($cap -and $cap.State -ne 'Installed') {
            Add-WindowsCapability -Online -Name $cap.Name
        }
        Start-Service sshd -ErrorAction SilentlyContinue
        Set-Service -Name sshd -StartupType Automatic -ErrorAction SilentlyContinue
        Log "sshd: $(Get-Service sshd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status)"
        $sshd = "$env:ProgramData\ssh\sshd_config"
        if (Test-Path $sshd) {
            $c = Get-Content $sshd -Raw
            if ($c -notmatch 'PubkeyAuthentication\s+yes') {
                Add-Content $sshd "`nPubkeyAuthentication yes`nPasswordAuthentication yes`n"
            }
        }
        Restart-Service sshd -Force -ErrorAction SilentlyContinue
    } catch { Log "OpenSSH: $_" }
} else { Log "SKIP OpenSSH service/capability (need admin)" }

# --- Firewall (admin) ---
Write-Step "Firewall TCP 22"
if ($isAdmin) {
    try {
        New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP-Mycosoft' -DisplayName 'OpenSSH Server (SSH) Mycosoft' `
            -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -ErrorAction SilentlyContinue | Out-Null
        Log "Firewall rule: ok or exists"
    } catch { Log "Firewall: $_" }
} else { Log "SKIP firewall (need admin)" }

# --- Password (interactive only) ---
if (-not $SkipPasswordPrompt) {
    Write-Step "Account password — skipped in non-interactive mode; use -SkipPasswordPrompt"
} else {
    Log "SkipPasswordPrompt: not changing password from this script."
}

Set-Content -Path $TagFile -Value "Mycosoft GPU Role=$Role`nHost=$env:COMPUTERNAME`nSSHSessionBootstrap=$(Get-Date -Format o)`nAdmin=$isAdmin`n"

# --- winget (user context often works) ---
Write-Step "winget"
$winget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $winget) {
    Log "winget not found — install App Installer from Microsoft Store."
} else {
    try {
        winget source update 2>&1 | Out-Null
        winget upgrade --all --accept-package-agreements --accept-source-agreements --include-unknown 2>&1 | Out-Null
    } catch { Log "winget upgrade: $_" }
}

$pkgs = @(
    @{ Id = 'Git.Git'; Name = 'Git' },
    @{ Id = 'Google.Chrome'; Name = 'Chrome' }
)
foreach ($p in $pkgs) {
    Write-Step "winget install $($p.Name)"
    try {
        winget install -e --id $p.Id --accept-package-agreements --accept-source-agreements --silent 2>&1 | Out-Null
    } catch { Log "winget $($p.Id): $_" }
}

Write-Step "NVIDIA GeForce Experience"
try {
    winget install -e --id Nvidia.GeForceExperience --accept-package-agreements --accept-source-agreements --silent 2>&1 | Out-Null
} catch { Log "GeForce Experience: $_" }

# --- WSL2 (often needs admin + reboot) ---
Write-Step "WSL2"
if ($isAdmin) {
    try {
        wsl --update 2>$null
        wsl --set-default-version 2 2>$null
        $dist = wsl -l -v 2>$null | Out-String
        if ($dist -notmatch 'Ubuntu') {
            wsl --install -d Ubuntu -n 2>&1 | Out-Null
            Log "WSL: Ubuntu install initiated; reboot may be required."
        } else {
            Log "WSL: Ubuntu already present."
        }
    } catch { Log "WSL: $_" }
} else { Log "SKIP wsl --install (need admin for first-time install)" }

# --- Docker Desktop ---
Write-Step "Docker Desktop"
if ($isAdmin) {
    try {
        winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    } catch { Log "Docker: $_" }
} else {
    try {
        winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    } catch { Log "Docker (non-admin attempt): $_" }
}

Write-Step "Done SSH-session bootstrap"
Log "If admin= False: log on via Chrome Remote Desktop and run Bootstrap-Legion-GPU.ps1 as Administrator once."
Log "Earth2 Python stack: run Setup-Earth2-Runtime.ps1 from the same folder."
