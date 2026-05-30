<#
.SYNOPSIS
    Build Side A MDP firmware and stage merged.bin + manifest for flash_executor.

.PARAMETER Env
    PlatformIO env: standalone, mushroom1, hyphae1

.PARAMETER Version
    Manifest version string (default side-a-mdp-2.1.0)

.EXAMPLE
    .\scripts\build_firmware_artifact.ps1 -Env standalone
#>
[CmdletBinding()]
param(
    [ValidateSet("standalone", "mushroom1", "hyphae1")]
    [string]$Env = "standalone",
    [string]$Version = "side-a-mdp-2.1.0"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$MycobrainRoot = Resolve-Path (Join-Path $RepoRoot "..\..\mycobrain")
$SideAPath = Join-Path $MycobrainRoot "firmware\MycoBrain_SideA_MDP"
$OutDir = Join-Path $RepoRoot "data\firmware_artifacts\$Version"
$BuildDir = Join-Path $SideAPath ".pio\build\$Env"

if (-not (Get-Command pio -ErrorAction SilentlyContinue)) {
    $pioCmd = @("python", "-m", "platformio")
} else {
    $pioCmd = @("pio")
}

Write-Host "Building $Env in $SideAPath" -ForegroundColor Cyan
Push-Location $SideAPath
try {
    & @pioCmd run -e $Env
    if ($LASTEXITCODE -ne 0) { throw "pio build failed" }
} finally {
    Pop-Location
}

$boot = Join-Path $BuildDir "bootloader.bin"
$part = Join-Path $BuildDir "partitions.bin"
$bootApp = Join-Path $BuildDir "boot_app0.bin"
$app = Join-Path $BuildDir "firmware.bin"
if (-not (Test-Path $bootApp)) {
    $frameworkBoot = Join-Path $env:USERPROFILE ".platformio\packages\framework-arduinoespressif32\tools\partitions\boot_app0.bin"
    if (-not (Test-Path $frameworkBoot)) {
        $frameworkBoot = "D:\Users\admin2\.platformio\packages\framework-arduinoespressif32\tools\partitions\boot_app0.bin"
    }
    if (Test-Path $frameworkBoot) {
        Copy-Item $frameworkBoot $bootApp
        Write-Host "Copied boot_app0.bin from framework package" -ForegroundColor DarkGray
    }
}
foreach ($f in @($boot, $part, $bootApp, $app)) {
    if (-not (Test-Path $f)) { throw "Missing build output: $f" }
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$Merged = Join-Path $OutDir "${Version}_${Env}_merged.bin"
$Manifest = Join-Path $OutDir "manifest.json"

Write-Host "Merging flash image -> $Merged" -ForegroundColor Yellow
python -m esptool --chip esp32s3 merge-bin `
    -o $Merged `
    --flash-size 16MB `
    0x0 $boot `
    0x8000 $part `
    0xe000 $bootApp `
    0x10000 $app
if ($LASTEXITCODE -ne 0) { throw "merge-bin failed" }

$hash = (Get-FileHash -Algorithm SHA256 -Path $Merged).Hash.ToLower()
$size = (Get-Item $Merged).Length
$manifestObj = @{
    version      = $Version
    role         = $Env
    side         = "a"
    board        = "esp32-s3-devkitc-1"
    flash_size   = "16MB"
    merged_bin   = (Split-Path -Leaf $Merged)
    offsets      = @{ merged = "0x0" }
    sha256       = $hash
    size_bytes   = $size
    built_at     = (Get-Date).ToUniversalTime().ToString("o")
    min_recovery = "mycobrain.sideA.bsec2"
}
$manifestJson = $manifestObj | ConvertTo-Json -Depth 4
Set-Content -Path $Manifest -Value $manifestJson
Write-Host "Artifact ready:" -ForegroundColor Green
Write-Host "  $Merged"
Write-Host "  sha256=$hash"
