# fix-claude-cowork-firewall.ps1
# Add Windows Firewall rules to allow Claude Cowork connections (ECONNRESET fix)
# Run as Administrator. MAR03 2026
#
# Error this addresses: "failed to write data: An established connection was aborted..."
# Claude Code process exited with code 255

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host "=== Claude Cowork Firewall Fix ===" -ForegroundColor Cyan
Write-Host "Adds outbound/inbound rules for Claude Desktop and Cowork VM" -ForegroundColor Gray
Write-Host ""

# Find Claude executable
$claudeExe = $null
$proc = Get-Process -Name "Claude" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($proc) {
    $claudeExe = $proc.Path
    Write-Host "Found Claude at: $claudeExe" -ForegroundColor Green
}

if (-not $claudeExe) {
    # Try WindowsApps (MSIX)
    $pkg = Get-AppxPackage -Name "*Claude*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pkg) {
        $installPath = $pkg.InstallLocation
        $claudeExe = Join-Path $installPath "Claude.exe"
        if (-not (Test-Path $claudeExe)) { $claudeExe = Join-Path $installPath "app\Claude.exe" }
        if (Test-Path $claudeExe) {
            Write-Host "Found Claude (MSIX) at: $claudeExe" -ForegroundColor Green
        } else {
            $claudeExe = $installPath  # Use folder as fallback
        }
    }
}

if (-not $claudeExe) {
    Write-Host "Claude not found. Start Claude Desktop first, or install it." -ForegroundColor Red
    exit 1
}

# Remove existing rules to avoid duplicates
Get-NetFirewallRule -DisplayName "Claude Desktop Out" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
Get-NetFirewallRule -DisplayName "Claude Desktop In" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
Get-NetFirewallRule -DisplayName "Claude Cowork VM" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue

# Add rules
if (Test-Path $claudeExe) {
    New-NetFirewallRule -DisplayName "Claude Desktop Out" -Direction Outbound -Program $claudeExe -Action Allow | Out-Null
    New-NetFirewallRule -DisplayName "Claude Desktop In" -Direction Inbound -Program $claudeExe -Action Allow | Out-Null
    Write-Host "Added firewall rules for Claude Desktop" -ForegroundColor Green
} else {
    # Directory - allow all in folder
    $dir = Split-Path $claudeExe -Parent
    Get-ChildItem $dir -Filter "*.exe" -ErrorAction SilentlyContinue | ForEach-Object {
        New-NetFirewallRule -DisplayName "Claude Desktop Out" -Direction Outbound -Program $_.FullName -Action Allow -ErrorAction SilentlyContinue | Out-Null
        New-NetFirewallRule -DisplayName "Claude Desktop In" -Direction Inbound -Program $_.FullName -Action Allow -ErrorAction SilentlyContinue | Out-Null
    }
    Write-Host "Added firewall rules for Claude Desktop (folder)" -ForegroundColor Green
}

# Cowork VM service
$svc = Get-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
if ($svc) {
    New-NetFirewallRule -DisplayName "Claude Cowork VM" -Direction Outbound -Service CoworkVMService -Action Allow -ErrorAction SilentlyContinue | Out-Null
    Write-Host "Added firewall rule for CoworkVMService" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Restart Claude Desktop and try Cowork again." -ForegroundColor Cyan
Write-Host "If still failing: temporarily disable Windows Defender real-time protection and test." -ForegroundColor Yellow
