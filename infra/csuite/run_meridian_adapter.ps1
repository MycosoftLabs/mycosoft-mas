# Meridian adapter runner — CFO VM bridge to MAS CFO MCP
# Date: March 8, 2026
# Run on CFO VM (192.168.0.193) to connect Perplexity desktop to MAS finance control plane
#
# Usage: .\run_meridian_adapter.ps1
#        .\run_meridian_adapter.ps1 -NoHttp
#        .\run_meridian_adapter.ps1 -HttpPort 8995

param(
    [switch]$NoHttp,
    [int]$HttpPort = 8995
)

$ErrorActionPreference = "Stop"
$MasRoot = if ($env:MAS_REPO_ROOT) { $env:MAS_REPO_ROOT } else { (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) }
$ScriptPath = Join-Path $MasRoot "scripts\run_meridian_adapter.py"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Meridian adapter script not found: $ScriptPath. Set MAS_REPO_ROOT or run from MAS repo."
}

$args = @()
if ($NoHttp) { $args += "--no-http" }
if ($HttpPort -ne 8995) { $args += "--http-port"; $args += $HttpPort }

Set-Location $MasRoot
& python $ScriptPath @args
