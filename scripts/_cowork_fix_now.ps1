# Claude Cowork FailedToOpenSocket - Fix Script (Run as Administrator)
# Mar 8 2026 - Aligns DNS, removes stale HNS, kills Claude

$logPath = "$env:TEMP\cowork_fix_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$log = { param($m) "[$(Get-Date -Format 'HH:mm:ss')] $m" | Tee-Object -FilePath $logPath -Append }

& $log "=== Cowork Fix Starting ==="

# 1. Set DNS on disconnected adapters (Ethernet 4, Ethernet per diagnostics)
$goodDns = @("1.1.1.1", "8.8.8.8")
$disconnected = Get-NetAdapter | Where-Object { $_.Status -eq "Disconnected" -and $_.Name -notlike "vEthernet*" }
foreach ($a in $disconnected) {
    try {
        Set-DnsClientServerAddress -InterfaceAlias $a.Name -ServerAddresses $goodDns -ErrorAction Stop
        & $log "Set DNS on $($a.Name) to $($goodDns -join ', ')"
    } catch {
        & $log "Set-Dns on $($a.Name) failed: $($_.Exception.Message)"
    }
}

# 2. Remove Cowork HNS endpoints and networks
try {
    $eps = Get-HnsEndpoint | Where-Object { $_.Name -like "cowork*" }
    $eps | ForEach-Object { Remove-HnsEndpoint -Id $_.Id -ErrorAction SilentlyContinue; & $log "Removed HNS endpoint $($_.Name)" }
    $nets = Get-HnsNetwork | Where-Object { $_.Name -like "cowork*" }
    $nets | ForEach-Object { Remove-HnsNetwork -Id $_.Id -ErrorAction SilentlyContinue; & $log "Removed HNS network $($_.Name)" }
} catch {
    & $log "HNS cleanup error: $($_.Exception.Message)"
}

# 3. Kill Claude
taskkill /F /IM Claude.exe /T 2>$null
& $log "Killed Claude (if running)"

& $log "=== Fix complete. Reopen Claude and launch Cowork. ==="
& $log "Log: $logPath"
