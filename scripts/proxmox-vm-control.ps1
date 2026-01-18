# Proxmox VM Control Script via API
# Controls VM 103 (mycosoft-sandbox)

$ProxmoxHost = "192.168.0.202"
$ProxmoxPort = 8006
$TokenId = "root@pam!cursor_mycocomp"
$TokenSecret = "9b86f08b-40ff-4eb9-b41b-93bc9e11700f"
$Node = "pve"
$VMID = 103

# Bypass SSL certificate validation
add-type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(
        ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) {
        return true;
    }
}
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Headers = @{
    "Authorization" = "PVEAPIToken=$TokenId=$TokenSecret"
}

$BaseUrl = "https://${ProxmoxHost}:${ProxmoxPort}/api2/json"

function Get-VMStatus {
    $response = Invoke-RestMethod -Uri "$BaseUrl/nodes/$Node/qemu/$VMID/status/current" -Headers $Headers -Method Get
    return $response.data
}

function Start-VM {
    Write-Host "Starting VM $VMID..."
    $response = Invoke-RestMethod -Uri "$BaseUrl/nodes/$Node/qemu/$VMID/status/start" -Headers $Headers -Method Post
    return $response
}

function Stop-VM {
    Write-Host "Stopping VM $VMID..."
    $response = Invoke-RestMethod -Uri "$BaseUrl/nodes/$Node/qemu/$VMID/status/stop" -Headers $Headers -Method Post
    return $response
}

function Restart-VM {
    Write-Host "Restarting VM $VMID..."
    $response = Invoke-RestMethod -Uri "$BaseUrl/nodes/$Node/qemu/$VMID/status/reboot" -Headers $Headers -Method Post
    return $response
}

function Get-VMConfig {
    $response = Invoke-RestMethod -Uri "$BaseUrl/nodes/$Node/qemu/$VMID/config" -Headers $Headers -Method Get
    return $response.data
}

# Execute guest command (requires QEMU Guest Agent)
function Invoke-GuestCommand {
    param([string]$Command)
    
    $body = @{
        command = $Command
    }
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/nodes/$Node/qemu/$VMID/agent/exec" -Headers $Headers -Method Post -Body $body
        return $response
    } catch {
        Write-Host "Guest Agent not available or command failed: $_"
        return $null
    }
}

# Get VM status
Write-Host "=== VM $VMID Status ==="
$status = Get-VMStatus
Write-Host "Status: $($status.status)"
Write-Host "CPU: $($status.cpu)"
Write-Host "Memory: $([math]::Round($status.mem / 1GB, 2)) GB"
Write-Host "Uptime: $($status.uptime) seconds"

# Check if QEMU Guest Agent is responding
Write-Host "`n=== Checking QEMU Guest Agent ==="
try {
    $agentInfo = Invoke-RestMethod -Uri "$BaseUrl/nodes/$Node/qemu/$VMID/agent/info" -Headers $Headers -Method Get
    Write-Host "QEMU Guest Agent: AVAILABLE"
    Write-Host "Agent Version: $($agentInfo.data.version)"
} catch {
    Write-Host "QEMU Guest Agent: NOT AVAILABLE (needs to be installed in VM)"
}

