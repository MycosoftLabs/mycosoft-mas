# Claude Cowork Fix - NO ADAPTER CHANGES
# Mar 10 2026 - Fixes: VM service, HNS cleanup, Plan9/virtiofs "bad address" (delete vm_bundles).
# Run as Administrator for HNS access.
# Fixes: FailedToOpenSocket, VM service not running, Plan9 mount failed: bad address,
#        HCS 0x800707de Construct failure (restart vmcompute/vmms)

$logPath = "$env:TEMP\cowork_fix_no_adapters_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$log = { param($m) "[$(Get-Date -Format 'HH:mm:ss')] $m" | Tee-Object -FilePath $logPath -Append }

& $log "=== Cowork Fix (NO ADAPTER CHANGES) ==="
& $log "This script does NOT modify Ethernet adapters or DNS."
& $log "Fixes: VM service, HNS, Plan9/virtiofs mount bad address, HCS 0x800707de."

# 1. Stop CoworkVMService (actual service name - NOT cowork-svc)
try {
    $svc = Get-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        Stop-Service -Name "CoworkVMService" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        & $log "Stopped CoworkVMService"
    } else {
        & $log "CoworkVMService not running or not found"
    }
} catch {
    & $log "CoworkVMService stop: $($_.Exception.Message)"
}

# 2. Kill Claude
taskkill /F /IM Claude.exe /T 2>$null
Start-Sleep -Seconds 2
& $log "Killed Claude (if running)"

# 2b. Reset VM runtime (fixes Plan9 "bad address" / virtiofs mount failure)
$claudeData = "$env:APPDATA\Claude"
foreach ($dir in @("vm_bundles", "claude-code-vm")) {
    $path = Join-Path $claudeData $dir
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction Stop
            & $log "Deleted $dir (VM runtime reset - fixes Plan9 mount)"
        } catch {
            & $log "WARN: Could not delete $dir : $($_.Exception.Message)"
        }
    } else {
        & $log "$dir not found, skipping"
    }
}
$tempClaude = "$env:TEMP\claude"
if (Test-Path $tempClaude) {
    try {
        Remove-Item -Path $tempClaude -Recurse -Force -ErrorAction Stop
        & $log "Deleted temp claude cache"
    } catch { & $log "Temp cache: $($_.Exception.Message)" }
}

# 3. Kill cowork VM via hcsdiag (if available)
try {
    $hcs = Get-Command hcsdiag -ErrorAction SilentlyContinue
    if ($hcs) {
        hcsdiag kill cowork-vm 2>$null
        & $log "hcsdiag kill cowork-vm executed"
    } else {
        & $log "hcsdiag not found, skipping"
    }
} catch {
    & $log "hcsdiag: $($_.Exception.Message)"
}

# 3b. Restart Hyper-V compute services (fixes HCS 0x800707de Construct failure)
try {
    foreach ($svcName in @("vmcompute", "vmms")) {
        $s = Get-Service -Name $svcName -ErrorAction SilentlyContinue
        if ($s) {
            Restart-Service -Name $svcName -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            & $log "Restarted $svcName"
        }
    }
} catch {
    & $log "Hyper-V restart: $($_.Exception.Message)"
}

# 4. Remove Cowork HNS endpoints and networks (no adapter changes)
try {
    $eps = Get-HnsEndpoint -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "cowork*" }
    if ($eps) {
        $eps | ForEach-Object {
            Remove-HnsEndpoint -Id $_.Id -ErrorAction SilentlyContinue
            & $log "Removed HNS endpoint: $($_.Name)"
        }
    } else {
        & $log "No cowork* HNS endpoints found"
    }
    $nets = Get-HnsNetwork -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "cowork*" }
    if ($nets) {
        $nets | ForEach-Object {
            Remove-HnsNetwork -Id $_.Id -ErrorAction SilentlyContinue
            & $log "Removed HNS network: $($_.Name)"
        }
    } else {
        & $log "No cowork* HNS networks found"
    }
} catch {
    & $log "HNS cleanup error: $($_.Exception.Message)"
}

# 5. Restart CoworkVMService so it rebuilds with clean HNS
try {
    Start-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    $svc = Get-Service -Name "CoworkVMService" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        & $log "CoworkVMService restarted successfully"
    } else {
        & $log "WARN: CoworkVMService may not have started. Try Repair/Reinstall."
    }
} catch {
    & $log "CoworkVMService start: $($_.Exception.Message)"
}

& $log "=== Fix complete ==="
& $log "Next: 1) Update Claude from claude.ai/download or Repair (Settings > Apps > Claude > Advanced > Repair)"
& $log "      2) Reopen Claude and launch Cowork."
& $log "Log: $logPath"
Write-Host "Done. Log: $logPath"
