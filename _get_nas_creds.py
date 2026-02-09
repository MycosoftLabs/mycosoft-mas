import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Get credentials from sandbox
sandbox_host = "192.168.0.187"
sandbox_user = "mycosoft"
sandbox_pass = "REDACTED_VM_SSH_PASSWORD"

print("Getting NAS credentials from Sandbox...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=sandbox_user, password=sandbox_pass, timeout=15)

# Get credentials
stdin, stdout, stderr = ssh.exec_command("sudo cat /etc/samba/mycosoft-nas.creds 2>/dev/null")
time.sleep(2)
creds = stdout.read().decode('utf-8', errors='replace').strip()
print(f"Credentials: {creds[:50]}...")

# Check NAS structure
print("\n=== NAS Structure ===")
stdin, stdout, stderr = ssh.exec_command("ls -la /mnt/mycosoft-nas/ | head -20")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Check existing directories
print("\n=== Key directories on NAS ===")
stdin, stdout, stderr = ssh.exec_command("du -sh /mnt/mycosoft-nas/*/ 2>/dev/null | head -15")
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Got NAS info!")
