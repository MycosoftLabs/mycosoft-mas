import paramiko
import time

# Proxmox host
proxmox_host = "192.168.0.90"
proxmox_user = "root"
proxmox_pass = "20202020"

print(f"Connecting to Proxmox at {proxmox_host}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(proxmox_host, username=proxmox_user, password=proxmox_pass, timeout=15)
    print("Connected to Proxmox!")
    
    # Check existing VMs
    print("\n=== Existing VMs ===")
    stdin, stdout, stderr = ssh.exec_command("qm list")
    print(stdout.read().decode())
    
    # Check storage
    print("\n=== Storage ===")
    stdin, stdout, stderr = ssh.exec_command("pvesm status")
    print(stdout.read().decode())
    
    # Check available ISOs
    print("\n=== Available ISOs ===")
    stdin, stdout, stderr = ssh.exec_command("ls -la /var/lib/vz/template/iso/ 2>/dev/null || echo 'No ISOs found in default path'")
    print(stdout.read().decode())
    
    # Check nodes
    print("\n=== Nodes ===")
    stdin, stdout, stderr = ssh.exec_command("pvesh get /nodes --output-format=json-pretty 2>/dev/null || pvecm nodes")
    output = stdout.read().decode()
    print(output[:1000] if len(output) > 1000 else output)
    
    ssh.close()
    print("\nReconnection successful!")
    
except Exception as e:
    print(f"Error: {e}")
