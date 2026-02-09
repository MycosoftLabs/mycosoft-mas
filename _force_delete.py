import paramiko
import time

wrong_host = "192.168.0.90"
proxmox_user = "root"
proxmox_pass = "20202020"

print(f"Force stopping and deleting VM from {wrong_host}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(wrong_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected!")

# Force stop
print("\n=== Force stopping VM 105 ===")
stdin, stdout, stderr = ssh.exec_command("qm stop 105 --skiplock --timeout 60")
time.sleep(20)
print(stdout.read().decode())
print(stderr.read().decode())

# Check status
stdin, stdout, stderr = ssh.exec_command("qm status 105")
time.sleep(2)
print("Status:", stdout.read().decode())

# Destroy
print("\n=== Destroying VM 105 ===")
stdin, stdout, stderr = ssh.exec_command("qm destroy 105 --purge --skiplock")
time.sleep(10)
print(stdout.read().decode())
print(stderr.read().decode())

# Verify
stdin, stdout, stderr = ssh.exec_command("qm list")
time.sleep(2)
print("VMs remaining:", stdout.read().decode())

ssh.close()
