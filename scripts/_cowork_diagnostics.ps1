# Claude Cowork FailedToOpenSocket diagnostics - Mar 6 2026
# Run as Administrator for full HNS output

$out = @()
$out += "=== COWORK DNS DIAGNOSTICS $(Get-Date) ==="

# 1. Network adapters
$out += "`n--- Network Adapters ---"
Get-NetAdapter | ForEach-Object { $out += "$($_.Name): $($_.Status) [$($_.InterfaceDescription)]" }

# 2. DNS per interface (IPv4 only)
$out += "`n--- DNS per Interface ---"
Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses.Count -gt 0 } | ForEach-Object {
    $out += "$($_.InterfaceAlias): $($_.ServerAddresses -join ', ')"
}

# 3. Cowork HNS endpoints (needs admin)
try {
    $out += "`n--- Cowork HNS Endpoints ---"
    $eps = Get-HnsEndpoint | Where-Object { $_.Name -like "cowork*" }
    if ($eps) {
        $eps | ForEach-Object { $out += "Name: $($_.Name); IP: $($_.IPAddress); Gateway: $($_.GatewayAddress); DNS: $($_.DNSServerList -join ', ')" }
    } else {
        $out += "No cowork* HNS endpoints found (or access denied)"
    }
} catch {
    $out += "HNS error: $($_.Exception.Message)"
}

# 4. Test api.anthropic.com resolution
$out += "`n--- DNS Resolution Test ---"
try {
    $r = Resolve-DnsName api.anthropic.com -ErrorAction Stop
    $out += "api.anthropic.com resolves: $($r[0].IPAddress)"
} catch {
    $out += "api.anthropic.com FAILED: $($_.Exception.Message)"
}

$out | Out-String
