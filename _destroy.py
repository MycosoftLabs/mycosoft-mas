import paramiko
import time

wrong_host = "192.168.0.90"
proxmox_user = "root"
proxmox_pass = "20202020"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(wrong_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected to wrong server, destroying VM...")

# Destroy VM
stdin, stdout, stderr = ssh.exec_command("qm destroy 105 --purge")
time.sleep(10)
print(stdout.read().decode())
print(stderr.read().decode())

# Verify
stdin, stdout, stderr = ssh.exec_command("qm list")
time.sleep(2)
result = stdout.read().decode()
print("VMs remaining:", result if result.strip() else "(none)")

ssh.close()
print("Cleanup complete!")
