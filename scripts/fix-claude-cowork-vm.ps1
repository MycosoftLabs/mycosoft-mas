# fix-claude-cowork-vm.ps1
# Troubleshooting script for "Failed to start Claude's workspace — VM service not running"
# Claude Desktop Cowork VM regression (v1.1.3189+). MAR03 2026
#
# Run from MAS repo root. Some steps require Administrator.

param(
    [switch]$ClearCache,
    [switch]$Force
)

$ErrorActionPreference = "Continue"

Write-Host "=== Claude Cowork VM Fix Script ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check Cowork VM service
Write-Host "1. Cowork VM Service status:" -ForegroundColor Yellow
$svc = Get-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "   Status: $($svc.Status)" -ForegroundColor $(if ($svc.Status -eq "Running") { "Green" } else { "Red" })
    if ($svc.Status -ne "Running") {
        Write-Host "   Attempting to start..." -ForegroundColor Yellow
        try {
            Start-Service CoworkVMService -ErrorAction Stop
            Write-Host "   Started successfully." -ForegroundColor Green
        } catch {
            Write-Host "   Failed: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "   Run this script as Administrator to start the service." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "   Service not found. Is Claude Desktop installed?" -ForegroundColor Red
}

# 2. Check Hyper-V
Write-Host ""
Write-Host "2. Hyper-V / Virtualization:" -ForegroundColor Yellow
$hv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -ErrorAction SilentlyContinue
if ($hv) {
    $state = $hv.State
    Write-Host "   Microsoft-Hyper-V: $state" -ForegroundColor $(if ($state -eq "Enabled") { "Green" } else { "Red" })
    if ($state -ne "Enabled") {
        Write-Host "   Run as Administrator: Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All" -ForegroundColor Yellow
        Write-Host "   Then reboot." -ForegroundColor Yellow
    }
} else {
    Write-Host "   Could not check (not Windows Pro/Enterprise?)" -ForegroundColor Yellow
}

$vmcompute = Get-Service vmcompute -ErrorAction SilentlyContinue
$vmms = Get-Service vmms -ErrorAction SilentlyContinue
Write-Host "   vmcompute: $($vmcompute.Status)" -ForegroundColor $(if ($vmcompute.Status -eq "Running") { "Green" } else { "Red" })
Write-Host "   vmms: $($vmms.Status)" -ForegroundColor $(if ($vmms.Status -eq "Running") { "Green" } else { "Red" })

# 3. Clear VM cache (optional)
if ($ClearCache -or $Force) {
    Write-Host ""
    Write-Host "3. Clearing VM bundle cache..." -ForegroundColor Yellow
    $bundlePath = "$env:APPDATA\Claude\vm_bundles"
    $vmPath = "$env:LOCALAPPDATA\Claude\claude-code-vm"
    if (Test-Path $bundlePath) {
        Remove-Item -Recurse -Force $bundlePath -ErrorAction SilentlyContinue
        Write-Host "   Removed $bundlePath" -ForegroundColor Green
    }
    if (Test-Path $vmPath) {
        Remove-Item -Recurse -Force $vmPath -ErrorAction SilentlyContinue
        Write-Host "   Removed $vmPath" -ForegroundColor Green
    }
    Write-Host "   Close Claude Desktop, then reopen. It will re-download the VM bundle." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "3. To clear VM cache, run: .\scripts\fix-claude-cowork-vm.ps1 -ClearCache" -ForegroundColor Gray
}

# 4. MSIX vs exe install
Write-Host ""
Write-Host "4. Install type:" -ForegroundColor Yellow
$claudePkg = Get-AppxPackage -Name "*Claude*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($claudePkg) {
    Write-Host "   MSIX (Store/WindowsApps) install detected." -ForegroundColor Yellow
    Write-Host "   MSIX has known path-resolution bugs. Consider uninstalling and using the" -ForegroundColor Yellow
    Write-Host "   .exe installer from https://claude.ai/download instead." -ForegroundColor Yellow
} else {
    Write-Host "   No MSIX package found (may be exe install - preferred)." -ForegroundColor Green
}

# 5. Log locations
Write-Host ""
Write-Host "5. Log locations (if Cowork still fails):" -ForegroundColor Yellow
Write-Host "   $env:APPDATA\Claude\Logs\cowork-service.log" -ForegroundColor Gray
Write-Host "   $env:APPDATA\Claude\Logs\cowork_vm_node.log" -ForegroundColor Gray
Write-Host ""
Write-Host "See docs\CLAUDE_COWORK_VM_TROUBLESHOOTING_MAR03_2026.md for full guide." -ForegroundColor Cyan
