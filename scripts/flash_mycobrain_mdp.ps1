param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("sidea", "sideb", "both")]
  [string]$Target,
  [string]$SideAPort = "COM7",
  [string]$SideBPort = "COM8"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$sideAPath = Join-Path $repo "firmware\MycoBrain_SideA_MDP"
$sideBPath = Join-Path $repo "firmware\MycoBrain_SideB_MDP"

function Build-And-Flash {
  param(
    [string]$ProjectPath,
    [string]$Port
  )
  Push-Location $ProjectPath
  try {
    Write-Host "Building $ProjectPath..."
    pio run
    Write-Host "Flashing $ProjectPath to $Port..."
    pio run -t upload --upload-port $Port
  } finally {
    Pop-Location
  }
}

switch ($Target) {
  "sidea" { Build-And-Flash -ProjectPath $sideAPath -Port $SideAPort }
  "sideb" { Build-And-Flash -ProjectPath $sideBPath -Port $SideBPort }
  "both" {
    Build-And-Flash -ProjectPath $sideAPath -Port $SideAPort
    Build-And-Flash -ProjectPath $sideBPath -Port $SideBPort
  }
}

Write-Host "Done."
