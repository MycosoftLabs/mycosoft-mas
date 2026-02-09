import paramiko
import time

proxmox_host = "192.168.0.90"
proxmox_user = "root"
proxmox_pass = "20202020"

print("Connecting to Proxmox...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(proxmox_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected!")

# Start the VM
print("\n=== Starting MINDEX VM (ID 105) ===")
stdin, stdout, stderr = ssh.exec_command("qm start 105")
time.sleep(5)
print(stdout.read().decode())
print(stderr.read().decode())

# Check status
print("\n=== VM Status ===")
stdin, stdout, stderr = ssh.exec_command("qm status 105")
time.sleep(2)
print(stdout.read().decode())

# List all VMs
print("\n=== All VMs ===")
stdin, stdout, stderr = ssh.exec_command("qm list")
time.sleep(2)
print(stdout.read().decode())

print("\nVM is starting. Cloud-init will configure networking...")
print("Waiting 60 seconds for boot and cloud-init...")

ssh.close()
