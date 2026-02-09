# Shutdown WSL to free vmmem memory - Feb 6, 2026
# vmmem = WSL2 virtual machine process. It can use 50%+ of RAM and slow the whole machine.
# Earth2 / GPU services run natively on Windows - they do NOT need WSL.
# Run this anytime the machine is slow; run once after adding .wslconfig to apply limits.

param(
    [switch]$ShutdownOnly  # Just shutdown WSL; don't prompt to disable features
)

$ErrorActionPreference = 'Stop'

Write-Host "`n=== WSL / vmmem memory fix ===" -ForegroundColor Cyan
Write-Host "vmmem is the WSL2 VM process. Shutting it down frees RAM.`n" -ForegroundColor Gray

# 1. Shutdown WSL (releases vmmem immediately)
try {
    wsl --shutdown 2>$null
    Write-Host "[OK] WSL shutdown sent. vmmem should release memory within a few seconds." -ForegroundColor Green
} catch {
    Write-Host "[INFO] wsl --shutdown completed (WSL may not have been running)." -ForegroundColor Yellow
}

# 2. Optional: kill vmmem process if it didn't exit (rare)
Start-Sleep -Seconds 2
$vmmem = Get-Process -Name "vmmem" -ErrorAction SilentlyContinue
if ($vmmem) {
    Write-Host "[INFO] vmmem still running ($([math]::Round($vmmem.WorkingSet64/1MB)) MB). It should drop soon." -ForegroundColor Yellow
    Write-Host "      If it stays high, restart the machine once after applying .wslconfig" -ForegroundColor Gray
} else {
    Write-Host "[OK] vmmem not running. Memory freed." -ForegroundColor Green
}

Write-Host "`nTo prevent WSL from using too much RAM in future:" -ForegroundColor Cyan
Write-Host "  1. Copy scripts\.wslconfig to %USERPROFILE%\.wslconfig" -ForegroundColor White
Write-Host "  2. Run: wsl --shutdown" -ForegroundColor White
Write-Host "  3. Restart WSL only when you need it (e.g. Docker).`n" -ForegroundColor White
