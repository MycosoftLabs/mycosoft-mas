# Dev Machine Cleanup - Feb 6, 2026
# Run when Cursor + whole machine is slow. Kills stale GPU Python processes and optionally WSL.
# Usage:
#   .\dev-machine-cleanup.ps1                    # List heavy processes only
#   .\dev-machine-cleanup.ps1 -KillStaleGPU     # Kill GPU-related Python only
#   .\dev-machine-cleanup.ps1 -ShutdownWSL      # Run wsl --shutdown
#   .\dev-machine-cleanup.ps1 -KillStaleGPU -ShutdownWSL  # Both

param(
    [switch]$KillStaleGPU,
    [switch]$ShutdownWSL
)

$ErrorActionPreference = 'Stop'

# Known script names that are GPU/dev services we can safely kill when cleaning up
$stalePatterns = @(
    'local_gpu_services',
    'start_personaplex',
    'personaplex_bridge_nvidia',
    'earth2_api_server',
    'mycobrain_service'
)

function Get-ProcessCommandLine($pid) {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $pid").CommandLine
        return $cmd
    } catch {
        return $null
    }
}

function Get-HeavyProcesses {
    Get-Process | Where-Object { $_.WorkingSet64 -gt 50MB } | Sort-Object WorkingSet64 -Descending
}

Write-Host "`n=== Dev machine resource check ===" -ForegroundColor Cyan

# 1. Top memory users
Write-Host "`nTop processes by memory (over 50 MB):" -ForegroundColor Yellow
$heavy = Get-HeavyProcesses
$heavy | Select-Object -First 25 | ForEach-Object {
    $mb = [math]::Round($_.WorkingSet64 / 1MB, 0)
    $name = $_.ProcessName
    Write-Host ("  {0,6} MB  {1} (PID {2})" -f $mb, $name, $_.Id)
}

# 2. Python processes and which are "stale" GPU
Write-Host "`nPython processes:" -ForegroundColor Yellow
$pythons = Get-Process -Name "python*" -ErrorAction SilentlyContinue
if (-not $pythons) {
    Write-Host "  None found."
} else {
    $toKill = @()
    foreach ($p in $pythons) {
        $cmd = Get-ProcessCommandLine $p.Id
        $mb = [math]::Round($p.WorkingSet64 / 1MB, 0)
        $stale = $false
        foreach ($pat in $stalePatterns) {
            if ($cmd -and $cmd -match [regex]::Escape($pat)) {
                $stale = $true
                break
            }
        }
        $tag = if ($stale) { " [STALE GPU - safe to kill]" } else { "" }
        $short = if ($cmd -and $cmd.Length -gt 0) { $cmd.Substring(0, [Math]::Min(70, $cmd.Length)) } else { "" }
        Write-Host ("  PID {0}  {1,5} MB  {2}{3}" -f $p.Id, $mb, $short, $tag)
        if ($stale) { $toKill += $p }
    }
    if ($KillStaleGPU -and $toKill.Count -gt 0) {
        Write-Host "`nKilling $($toKill.Count) stale GPU Python process(es)..." -ForegroundColor Red
        $toKill | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "Done." -ForegroundColor Green
    } elseif ($KillStaleGPU -and $toKill.Count -eq 0) {
        Write-Host "`nNo stale GPU Python processes to kill." -ForegroundColor Gray
    }
}

# 3. WSL
if ($ShutdownWSL) {
    Write-Host "`nShutting down WSL (frees vmmem)..." -ForegroundColor Yellow
    wsl --shutdown 2>$null
    Write-Host "Done." -ForegroundColor Green
} else {
    $vmmem = Get-Process -Name "vmmem" -ErrorAction SilentlyContinue
    if ($vmmem) {
        $mb = [math]::Round($vmmem.WorkingSet64 / 1MB, 0)
        Write-Host "`nvmmem (WSL) is using $mb MB. Run with -ShutdownWSL to free it." -ForegroundColor Yellow
    }
}

Write-Host "`nTip: Use 'npm run dev:next-only' when you don't need voice/Earth2 to avoid starting GPU services." -ForegroundColor Cyan
Write-Host ""
