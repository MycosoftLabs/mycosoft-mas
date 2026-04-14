# Run on your **dev PC** (same LAN as 4080A). Serves Quick-SSHD-LAN-Fix.ps1 — no copying files to the Legion.
# Requires: Python 3 on PATH (or install from microsoft store), OR run from folder and use built-in fallback.

param([int]$Port = 8790)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$file = 'Quick-SSHD-LAN-Fix.ps1'
if (-not (Test-Path (Join-Path $root $file))) { throw "Missing $file in $root" }

$lan = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -match '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)' -and $_.PrefixOrigin -ne 'WellKnown' } |
    Select-Object -ExpandProperty IPAddress -First 1
if (-not $lan) { $lan = 'YOUR_DEV_PC_LAN_IP' }

Write-Host @"

=== On this dev machine: leave this window open ===

=== On 4080A (192.168.0.249): Chrome Remote Desktop ===
    Open PowerShell **As Administrator** (required for firewall).

    Paste ONE line (replace if your dev PC IP is not $lan):

    iex (iwr -UseBasicParsing "http://${lan}:$Port/$file").Content

=== If download fails: Windows Firewall on THIS PC may block inbound $Port ===
    Run **once** as Admin on dev:
    New-NetFirewallRule -DisplayName "QuickFix HTTP" -Direction Inbound -LocalPort $Port -Protocol TCP -Action Allow

Press Ctrl+C to stop the server.

"@ -ForegroundColor Cyan

Set-Location $root
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    & python -m http.server $Port --bind 0.0.0.0
} else {
    Write-Host "Python not found; install Python 3 or run:  npx --yes http-server -p $Port -a 0.0.0.0" -ForegroundColor Yellow
    $npx = Get-Command npx -ErrorAction SilentlyContinue
    if ($npx) { & npx --yes http-server -p $Port -a 0.0.0.0 }
    else { throw "Install Python 3 or Node (npx) to serve files." }
}
