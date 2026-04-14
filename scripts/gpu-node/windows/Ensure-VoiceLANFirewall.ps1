#Requires -Version 5.1
<#
.SYNOPSIS
  Allow inbound TCP from LAN to Moshi, PersonaPlex bridge, and Ollama on the Voice Legion (default 241).

.NOTES
  Run elevated (Administrator) on the Voice Legion once.
  Defaults match python-process-registry / Start-LegionVoice-24x7.ps1.

.EXAMPLE
  .\Ensure-VoiceLANFirewall.ps1
#>
param(
    [int]$MoshiPort = 8998,
    [int]$BridgePort = 8999,
    [int]$OllamaPort = 11434,
    [string]$RulePrefix = "Mycosoft Voice GPU"
)

$ErrorActionPreference = "Stop"

function Ensure-Rule([string]$Name, [int]$Port) {
    $show = netsh advfirewall firewall show rule name="$Name" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Exists: $Name"
        return
    }
    netsh advfirewall firewall add rule name="$Name" dir=in action=allow protocol=TCP localport=$Port profile=private,domain | Out-Null
    Write-Host "Added: $Name (TCP $Port)"
}

Ensure-Rule "$RulePrefix Moshi" $MoshiPort
Ensure-Rule "$RulePrefix Bridge" $BridgePort
Ensure-Rule "$RulePrefix Ollama" $OllamaPort
