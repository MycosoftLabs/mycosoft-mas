import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Getting exact credentials from Sandbox...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Check all possible credential sources
print("=== Checking all credential files ===")
cmds = [
    "sudo cat /etc/samba/mycosoft-nas.creds 2>/dev/null || echo 'Not found'",
    "sudo cat /root/.smbcredentials 2>/dev/null || echo 'Not found'",
    "sudo cat /home/mycosoft/.smbcredentials 2>/dev/null || echo 'Not found'",
    "sudo grep -r 'password' /etc/samba/ 2>/dev/null || echo 'None'",
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(2)
    result = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"{cmd[:50]}...\n{result}\n")

# Get fstab entry
print("=== Fstab entries ===")
stdin, stdout, stderr = ssh.exec_command("cat /etc/fstab | grep 192.168.0.105")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
