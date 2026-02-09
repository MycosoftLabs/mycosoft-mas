import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

proxmox_host = "192.168.0.202"
proxmox_user = "root"
proxmox_pass = "20202020"

print(f"Connecting to Proxmox at {proxmox_host}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(proxmox_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected!")

# Start VM
print("\n=== Starting VM 189 ===")
stdin, stdout, stderr = ssh.exec_command("qm start 189")
time.sleep(5)
print(stdout.read().decode('utf-8', errors='replace'))

# Check status
stdin, stdout, stderr = ssh.exec_command("qm status 189")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# List all VMs
print("\n=== All VMs ===")
stdin, stdout, stderr = ssh.exec_command("qm list")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("VM started! Waiting for boot...")
