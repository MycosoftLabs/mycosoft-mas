#Requires -Version 5.1
<#
.SYNOPSIS
  Allow inbound TCP to Earth-2 API port from the LAN (so MAS / dev PCs can curl 192.168.0.249:8220).

.NOTES
  Run elevated (Administrator) on the Earth-2 Legion once, or after firewall reset.
  Complements Ensure-Earth2WSLPortProxy.ps1 (WSL -> host forwarding).

.EXAMPLE
  .\Ensure-Earth2LANFirewall.ps1 -Port 8220
#>
param(
    [int]$Port = 8220,
    [string]$RuleName = "Mycosoft Earth-2 API (LAN inbound)"
)

$ErrorActionPreference = "Stop"

$existing = netsh advfirewall firewall show rule name="$RuleName" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Rule already exists: $RuleName"
    exit 0
}

netsh advfirewall firewall add rule name="$RuleName" dir=in action=allow protocol=TCP localport=$Port profile=private,domain | Out-Null
Write-Host "Added firewall rule: $RuleName (TCP $Port, private/domain)"
