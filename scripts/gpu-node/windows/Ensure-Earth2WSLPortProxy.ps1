#Requires -Version 5.1
<#
.SYNOPSIS
  Forward Windows host TCP port (default 8220) to the current WSL2 distro IPv4 address so LAN clients can reach Earth2 API.

.NOTES
  WSL2 uses a NAT address that changes after reboot; run this at startup (Task Scheduler) after WSL is up.
  Requires permission to run netsh interface portproxy (often Administrator).

.EXAMPLE
  .\Ensure-Earth2WSLPortProxy.ps1 -ListenPort 8220 -WslDistro Ubuntu
#>
param(
    [string]$WslDistro = "Ubuntu",
    [int]$ListenPort = 8220,
    [string]$ListenAddress = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
if ($env:MYCOSOFT_WSL_DISTRO) { $WslDistro = $env:MYCOSOFT_WSL_DISTRO }

$wslIp = (& wsl -d $WslDistro -u root -- hostname -I).Trim().Split()[0]
if (-not $wslIp) { throw "Could not read WSL IP (is WSL running?)" }

$existing = netsh interface portproxy show v4tov4 | Out-String
if ($existing -match "${ListenAddress}:${ListenPort}") {
    netsh interface portproxy delete v4tov4 listenaddress=$ListenAddress listenport=$ListenPort | Out-Null
}

netsh interface portproxy add v4tov4 listenaddress=$ListenAddress listenport=$ListenPort connectaddress=$wslIp connectport=$ListenPort | Out-Null
Write-Host "portproxy ${ListenAddress}:${ListenPort} -> ${wslIp}:${ListenPort}"
