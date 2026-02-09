import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Find any file containing password or morgan
print("=== Searching for credential files ===")
cmds = [
    "sudo find /etc -name '*cred*' -type f 2>/dev/null",
    "sudo find /root -name '*smb*' -type f 2>/dev/null",
    "sudo ls -la /etc/samba/ 2>/dev/null || echo 'No samba dir'",
    "sudo cat /etc/samba/* 2>/dev/null || echo 'No files'",
    "sudo ls -la /root/.smb* 2>/dev/null || echo 'No .smb files'",
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(2)
    result = stdout.read().decode('utf-8', errors='replace').strip()
    if result and result != "No samba dir" and result != "No files":
        print(f"{cmd}\n{result}\n")

# Check if this machine was manually configured
print("=== Bash history for mount commands ===")
stdin, stdout, stderr = ssh.exec_command("cat ~/.bash_history | grep -i 'mount\\|cifs\\|samba' | head -20")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Check cloud-init
print("=== Cloud-init user data ===")
stdin, stdout, stderr = ssh.exec_command("sudo cat /var/lib/cloud/instance/user-data.txt 2>/dev/null | head -50 || echo 'No cloud-init'")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
