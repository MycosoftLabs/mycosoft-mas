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
    MYCOSOFT_WSL_DISTRO     default Ubuntu
    MYCOSOFT_EARTH2_VENV    full path to activate script inside WSL
    MYCOSOFT_EARTH2_REPO    repo root inside WSL
#>
param(
    [string]$WslDistro = "Ubuntu",
    [string]$WslVenvActivate = "/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/activate",
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
if ($env:MYCOSOFT_EARTH2_VENV) { $WslVenvActivate = $env:MYCOSOFT_EARTH2_VENV }
if ($env:MYCOSOFT_EARTH2_REPO) { $WslRepoRoot = $env:MYCOSOFT_EARTH2_REPO }

$logWsl = "$WslRepoRoot/earth2-api-nohup.log".Replace('\', '/')
# bash -lc one line: activate, exports, nohup python in background (paths must not contain spaces for this simple form)
$bashLine = "source $WslVenvActivate && export EARTH2_API_HOST=0.0.0.0 && export EARTH2_API_PORT=$ApiPort && cd $WslRepoRoot && nohup python scripts/earth2_api_server.py >> $logWsl 2>&1 &"

L "Starting Earth2 API in WSL ($WslDistro)..."
wsl -d $WslDistro -u root -- bash -lc $bashLine
L "Launched. Tail log in WSL: $logWsl  API: http://<this-host-LAN-IP>:${ApiPort}/docs"
