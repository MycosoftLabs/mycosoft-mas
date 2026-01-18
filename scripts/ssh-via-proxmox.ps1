# SSH to VM via Proxmox Host
# This script SSHes to Proxmox first, then to the VM

$ProxmoxHost = "192.168.0.202"
$ProxmoxUser = "root"
$ProxmoxPass = "20202020"
$VMIp = "192.168.0.87"
$VMUser = "mycosoft"
$VMPass = "REDACTED_VM_SSH_PASSWORD"

# Method 1: Direct SSH to VM (if SSH is installed)
Write-Host "=== Testing Direct SSH to VM ==="
Write-Host "Attempting SSH to $VMUser@$VMIp..."

# Check if SSH port is open
$tcpClient = New-Object System.Net.Sockets.TcpClient
$tcpClient.ReceiveTimeout = 3000
$tcpClient.SendTimeout = 3000

try {
    $connection = $tcpClient.BeginConnect($VMIp, 22, $null, $null)
    $wait = $connection.AsyncWaitHandle.WaitOne(3000, $false)
    
    if ($wait -and $tcpClient.Connected) {
        Write-Host "SSH Port 22 is OPEN on $VMIp"
        $tcpClient.Close()
        
        # Try SSH connection
        Write-Host "SSH is available - you can connect with:"
        Write-Host "  ssh $VMUser@$VMIp"
        Write-Host "  Password: $VMPass"
    } else {
        Write-Host "SSH Port 22 is CLOSED on $VMIp - SSH server not installed yet"
        $tcpClient.Close()
    }
} catch {
    Write-Host "Cannot reach $VMIp on port 22"
}

# Method 2: SSH to Proxmox and execute commands on VM via qm terminal
Write-Host "`n=== Proxmox Host SSH Method ==="
Write-Host "SSH to Proxmox: ssh $ProxmoxUser@$ProxmoxHost"
Write-Host "Then use: qm terminal 103"
Write-Host "Or use: qm guest exec 103 -- <command> (requires guest agent)"

