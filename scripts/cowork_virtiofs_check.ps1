# Claude CoWork virtiofs / sandbox diagnostic script (Windows)
# Created: February 12, 2026
# Run in PowerShell (no admin required for checks)

Write-Host "`n=== Claude CoWork virtiofs diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# 1. Virtualization
Write-Host "[1] Virtualization" -ForegroundColor Yellow
try {
    $hyperv = systeminfo 2>$null | Select-String -Pattern "Hyper-V"
    if ($hyperv) {
        Write-Host "  Hyper-V / VM info: $hyperv"
    } else {
        Write-Host "  systeminfo did not show Hyper-V line (may be OK on Home SKU)"
    }
} catch {
    Write-Host "  Could not run systeminfo: $_"
}

$vmPlatform = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -ErrorAction SilentlyContinue
if ($vmPlatform) {
    Write-Host "  VirtualMachinePlatform: $($vmPlatform.State)"
} else {
    Write-Host "  VirtualMachinePlatform: (feature check not available - need Admin?)"
}
Write-Host ""

# 2. CoWork data locations
Write-Host "[2] CoWork data locations" -ForegroundColor Yellow
$paths = @(
    "$env:APPDATA\claude-cowork",
    "$env:LOCALAPPDATA\claude-cowork",
    "$env:LOCALAPPDATA\Claude",
    "$env:APPDATA\Anthropic"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "  EXISTS: $p"
        Get-ChildItem $p -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    - $($_.Name)" }
    } else {
        Write-Host "  (not found): $p"
    }
}
Write-Host ""

# 3. CoWork process
Write-Host "[3] CoWork-related processes" -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -match "claude|cowork|sandbox" } | ForEach-Object {
    Write-Host "  $($_.ProcessName) (PID $($_.Id))"
}
if (-not (Get-Process | Where-Object { $_.ProcessName -match "claude|cowork|sandbox" })) {
    Write-Host "  None running (OK if CoWork is closed)"
}
Write-Host ""

# 4. Suggested next steps
Write-Host "[4] Suggested next steps" -ForegroundColor Green
Write-Host "  1. Fully quit CoWork, then run it again."
Write-Host "  2. If still failing, clear sandbox: remove contents of:"
Write-Host "     $env:APPDATA\claude-cowork"
Write-Host "  3. Try running CoWork as Administrator (right-click exe)."
Write-Host "  4. Ensure Windows is updated and CoWork is latest version."
Write-Host ""
Write-Host "Full guide: docs\CLAUDE_COWORK_VIRTIOFS_FIX_WINDOWS_FEB12_2026.md" -ForegroundColor Cyan
Write-Host ""
