param(
  [Parameter(Mandatory = $true)]
  [string]$OnDeviceHost,
  [Parameter(Mandatory = $true)]
  [string]$GatewayHost,
  [string]$SshUser = "mycosoft",
  [switch]$FlashFirmware,
  [string]$SideAPort = "COM7",
  [string]$SideBPort = "COM8"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$remoteRoot = "/opt/mycosoft/mas"

function Invoke-RemoteSetup {
  param(
    [string]$Host,
    [string]$Mode
  )

  Write-Host "Configuring $Mode service on $Host..."
  $cmd = @(
    "set -euo pipefail",
    "cd $remoteRoot",
    "sudo bash deploy/jetson/install_jetson_services.sh $Mode",
    "sudo systemctl is-active mycobrain-$($Mode -replace 'ondevice','ondevice-operator' -replace 'gateway','gateway-router') || true"
  ) -join "; "

  ssh "$SshUser@$Host" $cmd
}

if ($FlashFirmware) {
  Write-Host "Flashing Side A and Side B firmware..."
  & (Join-Path $repo "scripts\flash_mycobrain_mdp.ps1") -Target both -SideAPort $SideAPort -SideBPort $SideBPort
}

Invoke-RemoteSetup -Host $OnDeviceHost -Mode "ondevice"
Invoke-RemoteSetup -Host $GatewayHost -Mode "gateway"

Write-Host "Bring-up flow completed."
