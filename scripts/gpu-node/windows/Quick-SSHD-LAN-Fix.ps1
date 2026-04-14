#Requires -RunAsAdministrator
# Fixes: sshd not reachable on LAN — firewall + service + password auth.
# Run ON the Legion (4080A) in PowerShell **As Administrator**.
# No repo copy needed: see Serve-QuickFix.ps1 on dev PC for one-line pull.

$ErrorActionPreference = 'Stop'

Write-Host 'Starting sshd and opening TCP 22 on Private networks...' -ForegroundColor Cyan

# Service
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd

# Firewall: enable built-in OpenSSH rules + explicit rule (Private/Public/Domain)
Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'OpenSSH' } |
    Enable-NetFirewallRule -ErrorAction SilentlyContinue
if (-not (Get-NetFirewallRule -Name 'Mycosoft-SSH-22' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'Mycosoft-SSH-22' -DisplayName 'Mycosoft SSH TCP 22' `
        -Enabled True -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22 `
        -Profile Domain, Private, Public
}
# Fallback (works even if NetSecurity cmdlets act odd)
netsh advfirewall firewall delete rule name="Mycosoft-SSH-22-netsh" 2>$null
netsh advfirewall firewall add rule name="Mycosoft-SSH-22-netsh" dir=in action=allow protocol=TCP localport=22

# Password logon (required if no key yet)
$cfg = Join-Path $env:ProgramData 'ssh\sshd_config'
if (Test-Path $cfg) {
    $t = Get-Content $cfg -Raw
    if ($t -notmatch '(?m)^PasswordAuthentication\s+yes') {
        Add-Content $cfg "`nPasswordAuthentication yes`nPubkeyAuthentication yes`n"
    }
    Restart-Service sshd -Force
}

# Listen on all interfaces (default — only uncomment if you changed ListenAddress)
# Ensure no ListenAddress 127.0.0.1 only

Write-Host "`nListening on port 22:" -ForegroundColor Green
Get-NetTCPConnection -State Listen -LocalPort 22 -ErrorAction SilentlyContinue | Format-Table
Get-Service sshd | Format-List Status, StartType
Write-Host 'From another PC on the LAN: ssh USER@192.168.0.249' -ForegroundColor Green
