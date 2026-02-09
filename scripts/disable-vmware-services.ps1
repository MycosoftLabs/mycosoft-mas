# Disable VMware Services - Feb 6, 2026
# Mycosoft uses Proxmox for VMs; VMware should not run on this dev machine.
# Run as Administrator to stop and disable all VMware-related services.

$vmwareServices = @(
    'VMAuthdService',      # VMware Authorization
    'VMUSBArbService',     # VMware USB
    'VMnetDHCP',           # VMware DHCP
    'VMware NAT Service',  # VMware NAT
    'VMwareHostOpen',      # VMware Host
    'VGAuthService',       # VMware Guest Auth
    'vmware-authd',        # Alternative name
    'VMwareWorkstation'    # Workstation service
)

$stopped = 0
$disabled = 0

foreach ($name in $vmwareServices) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $svc) {
        $svc = Get-Service | Where-Object { $_.DisplayName -like "*VMware*" -or $_.DisplayName -eq $name } | Select-Object -First 1
    }
    if ($svc) {
        Write-Host "Found: $($svc.Name) - $($svc.DisplayName) (Status: $($svc.Status), Start: $($svc.StartType))"
        if ($svc.Status -eq 'Running') {
            try {
                Stop-Service -Name $svc.Name -Force -ErrorAction Stop
                Write-Host "  Stopped."
                $stopped++
            } catch {
                Write-Host "  Stop failed: $_"
            }
        }
        if ($svc.StartType -ne 'Disabled') {
            try {
                & $env:SystemRoot\System32\sc.exe config $svc.Name start= disabled
                Write-Host "  Disabled (will not start on boot)."
                $disabled++
            } catch {
                Write-Host "  Disable failed (run as Administrator): $_"
            }
        }
    }
}

# Also disable any service with "VMware" in display name
Get-Service | Where-Object { $_.DisplayName -like "*VMware*" } | ForEach-Object {
    if ($vmwareServices -notcontains $_.Name) {
        Write-Host "Found: $($_.Name) - $($_.DisplayName)"
        if ($_.Status -eq 'Running') {
            try { Stop-Service -Name $_.Name -Force -ErrorAction Stop; $stopped++ } catch {}
        }
        try {
            & $env:SystemRoot\System32\sc.exe config $_.Name start= disabled
            $disabled++
        } catch {}
    }
}

Write-Host "`nDone. Stopped: $stopped service(s), Disabled: $disabled service(s)."
Write-Host "VMware will not start automatically. Proxmox is used for VMs."

# Optionally kill VMware processes if running (VMware Workstation app, etc.)
$procs = Get-Process | Where-Object { $_.ProcessName -match "vmware|vmnat|vmnet|vmount|vmvga|VGAuth" }
if ($procs) {
    Write-Host "`nStopping VMware processes: $($procs.ProcessName -join ', ')"
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped."
}
