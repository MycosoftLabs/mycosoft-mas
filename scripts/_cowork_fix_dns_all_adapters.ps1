# Claude Cowork Fix - Set DNS on ALL adapters + HNS cleanup
# Mar 03 2026 - Fixes: "Can't reach Claude API" by ensuring every adapter has 1.1.1.1/8.8.8.8
# Root cause: cowork-svc.exe picks DNS from any adapter (including disconnected).
# Run as Administrator.
# Ref: anthropics/claude-code #25144, #28516

$logPath = "$env:TEMP\cowork_fix_dns_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$log = { param($m) "[$(Get-Date -Format 'HH:mm:ss')] $m" | Tee-Object -FilePath $logPath -Append }

& $log "=== Cowork Fix: DNS on ALL adapters + HNS ==="

# 1. Set DNS on ALL adapters (cowork grabs from whichever it finds)
$goodDns = @("1.1.1.1", "8.8.8.8")
$adapters = Get-NetAdapter | Where-Object { $_.Status -in @("Up", "Disconnected") -and $_.InterfaceDescription -notlike "*Loopback*" }
foreach ($a in $adapters) {
    try {
        $current = (Get-DnsClientServerAddress -InterfaceAlias $a.Name -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses
        # Preserve gateway DNS (192.168.x.x) as first if present, then add public
        $gatewayDns = @($current | Where-Object { $_ -match "^\d+\.\d+\.\d+\.\d+$" -and $_ -notin $goodDns })
        $servers = @($gatewayDns) + $goodDns | Select-Object -Unique
        Set-DnsClientServerAddress -InterfaceAlias $a.Name -ServerAddresses $servers -ErrorAction Stop
        & $log "Set DNS on $($a.Name): $($servers -join ', ')"
    } catch {
        & $log "WARN: $($a.Name): $($_.Exception.Message)"
    }
}

# 2. Stop CoworkVMService
try {
    Stop-Service -Name "CoworkVMService" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    & $log "Stopped CoworkVMService"
} catch { & $log "Stop: $($_.Exception.Message)" }

# 3. Kill Claude
taskkill /F /IM Claude.exe /T 2>$null
Start-Sleep -Seconds 2
& $log "Killed Claude"

# 4. Delete vm_bundles and claude-code-vm (force fresh VM)
foreach ($dir in @("vm_bundles", "claude-code-vm")) {
    $path = Join-Path "$env:APPDATA\Claude" $dir
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction Stop
            & $log "Deleted $dir"
        } catch { & $log "Delete $dir : $($_.Exception.Message)" }
    }
}
if (Test-Path "$env:TEMP\claude") {
    Remove-Item -Path "$env:TEMP\claude" -Recurse -Force -ErrorAction SilentlyContinue
    & $log "Deleted temp claude cache"
}

# 5. Optional: Disable SharedAccess (ICS) - can interfere with Hyper-V NAT
try {
    $sa = Get-Service SharedAccess -ErrorAction SilentlyContinue
    if ($sa -and $sa.Status -eq "Running") {
        Stop-Service SharedAccess -Force -ErrorAction SilentlyContinue
        Set-Service SharedAccess -StartupType Disabled -ErrorAction SilentlyContinue
        & $log "Disabled SharedAccess (ICS)"
    }
} catch { & $log "SharedAccess: $($_.Exception.Message)" }

# 6. Kill cowork VM
try {
    if (Get-Command hcsdiag -ErrorAction SilentlyContinue) {
        hcsdiag kill cowork-vm 2>$null
        & $log "hcsdiag kill cowork-vm"
    }
} catch { }

# 7. Restart Hyper-V services
foreach ($svcName in @("vmcompute", "vmms")) {
    try {
        Restart-Service -Name $svcName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        & $log "Restarted $svcName"
    } catch { }
}

# 8. Remove Cowork HNS endpoints and networks
try {
    Get-HnsEndpoint -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "cowork*" } | ForEach-Object {
        Remove-HnsEndpoint -Id $_.Id -ErrorAction SilentlyContinue
        & $log "Removed HNS endpoint: $($_.Name)"
    }
    Get-HnsNetwork -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "cowork*" } | ForEach-Object {
        Remove-HnsNetwork -Id $_.Id -ErrorAction SilentlyContinue
        & $log "Removed HNS network: $($_.Name)"
    }
} catch {
    & $log "HNS: $($_.Exception.Message)"
}

# 9. Remove NetNat cowork (if exists - can block routing)
try {
    Get-NetNat | Where-Object { $_.Name -like "*cowork*" } | Remove-NetNat -Confirm:$false -ErrorAction SilentlyContinue
    & $log "Removed cowork NetNat"
} catch { }

# 10. Restart CoworkVMService
try {
    Start-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    $svc = Get-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        & $log "CoworkVMService started"
    } else {
        & $log "WARN: CoworkVMService may not have started"
    }
} catch {
    & $log "Start: $($_.Exception.Message)"
}

& $log "=== Done ==="
& $log "Next: Repair Claude (Settings > Apps > Claude > Advanced > Repair), then reopen and launch Cowork."
Write-Host "Done. Log: $logPath"
