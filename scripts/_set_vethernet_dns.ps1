# Set DNS on vEthernet adapters - Cowork VM uses these, empty DNS = can't resolve api.anthropic.com
# Run as Admin. Does NOT touch Ethernet 2 (active connection).
$adapters = @('vEthernet (WSL (Hyper-V firewall))', 'vEthernet (Default Switch)')
$dns = @('1.1.1.1', '8.8.8.8')
foreach ($a in $adapters) {
  try {
    Set-DnsClientServerAddress -InterfaceAlias $a -ServerAddresses $dns -ErrorAction Stop
    Write-Host "Set DNS on $a to 1.1.1.1, 8.8.8.8"
  } catch {
    Write-Host "Failed $a : $_"
  }
}
