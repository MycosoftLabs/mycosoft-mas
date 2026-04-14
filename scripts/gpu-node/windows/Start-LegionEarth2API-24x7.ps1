#Requires -Version 5.1
<#
.SYNOPSIS
  Start Earth2 Studio API (uvicorn) inside WSL Ubuntu where earth2studio is installed.

.NOTES
  Default WSL layout from Invoke-WSLGPUNodeSetup.ps1 -Role Earth2:
    /root/mycosoft-venvs/mycosoft-earth2-wsl
    /root/mycosoft-mas

  Binds EARTH2_API_HOST=0.0.0.0 for LAN access from MAS/CREP (port 8220).

  Env overrides (Windows):
    MYCOSOFT_WSL_DISTRO   default Ubuntu
    MYCOSOFT_EARTH2_PYTHON  venv python inside WSL (default below)
    MYCOSOFT_EARTH2_REPO    repo root inside WSL
#>
param(
    [string]$WslDistro = "Ubuntu",
    [string]$WslPython = "/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/python",
    [string]$WslRepoRoot = "/root/mycosoft-mas",
    [int]$ApiPort = 8220,
    [switch]$SkipFirewall
)

$ErrorActionPreference = 'Stop'
$LogDir = Join-Path $env:USERPROFILE "MycosoftData\logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir "earth2-api-wsl-bootstrap.log"

function L([string]$m) {
    $line = "$(Get-Date -Format o) $m"
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

if (-not $SkipFirewall) {
    $name = "Mycosoft-Earth2-API-$ApiPort"
    $existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $name -Direction Inbound `
            -LocalPort $ApiPort -Protocol TCP -Action Allow `
            -RemoteAddress 192.168.0.0/24 -Profile Private,Domain | Out-Null
        L "Firewall: allowed LAN -> TCP $ApiPort"
    }
}

if ($env:MYCOSOFT_WSL_DISTRO) { $WslDistro = $env:MYCOSOFT_WSL_DISTRO }
if ($env:MYCOSOFT_EARTH2_PYTHON) { $WslPython = $env:MYCOSOFT_EARTH2_PYTHON }
if ($env:MYCOSOFT_EARTH2_REPO) { $WslRepoRoot = $env:MYCOSOFT_EARTH2_REPO }

$logWsl = "$WslRepoRoot/earth2-api-nohup.log".Replace('\', '/')
$daemonSh = "$WslRepoRoot/scripts/gpu-node/wsl/run-earth2-api-daemon.sh".Replace('\', '/')
# Detach from PowerShell: spawn WSL in a new process (nohup inside WSL was unreliable via bash -lc from Win32).
$bashLine = "chmod +x `"$daemonSh`" 2>/dev/null; export EARTH2_API_HOST=0.0.0.0; export EARTH2_API_PORT=$ApiPort; export MYCOSOFT_EARTH2_REPO=$WslRepoRoot; export MYCOSOFT_EARTH2_PYTHON=$WslPython; nohup bash `"$daemonSh`" </dev/null >/dev/null 2>&1 &"

L "Starting Earth2 API in WSL ($WslDistro) detached..."
$psi = Start-Process -FilePath "wsl.exe" -ArgumentList @(
    "-d", $WslDistro, "-u", "root", "--", "bash", "-lc", $bashLine
) -WindowStyle Hidden -PassThru
L "WSL launcher PID: $($psi.Id). Tail log in WSL: $logWsl  API: http://<this-host-LAN-IP>:${ApiPort}/docs"
