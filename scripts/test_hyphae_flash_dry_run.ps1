# Hyphae Pi flash dry-run (Phase B3) — requires SSH credentials on 228
param(
    [switch]$LiveFlash
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$creds = Join-Path $repo ".credentials.local"
if (Test-Path $creds) {
    Get-Content $creds | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$artifact = Join-Path $repo "data/firmware_artifacts/side-a-mdp-2.1.0/side-a-mdp-2.1.0_hyphae1_merged.bin"
if (-not (Test-Path $artifact)) {
    throw "Missing hyphae1 artifact: $artifact"
}

$argsList = @(
    "scripts/hyphae_pi_flash.py",
    "--host", "192.168.0.228",
    "--artifact", $artifact
)
if ($LiveFlash) {
    $env:APPROVE_FLASH = "true"
    $argsList += @("--confirm")
} else {
    $argsList += @("--dry-run")
}

Write-Host "Hyphae flash: host=192.168.0.228 profile=hyphae1 live=$LiveFlash"
Push-Location $repo
try {
    python @argsList
} finally {
    Pop-Location
}
