import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Final credential search on Sandbox...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# The fstab references /etc/samba/mycosoft-nas.creds - check if it exists
print("=== Checking exact file path ===")
stdin, stdout, stderr = ssh.exec_command("sudo ls -la /etc/samba/")
time.sleep(2)
print("Dir listing:", stdout.read().decode('utf-8', errors='replace'))

stdin, stdout, stderr = ssh.exec_command("sudo test -f /etc/samba/mycosoft-nas.creds && echo 'EXISTS' || echo 'MISSING'")
time.sleep(2)
exists = stdout.read().decode('utf-8', errors='replace').strip()
print(f"File exists: {exists}")

if exists == "EXISTS":
    stdin, stdout, stderr = ssh.exec_command("sudo cat /etc/samba/mycosoft-nas.creds")
    time.sleep(2)
    creds = stdout.read().decode('utf-8', errors='replace')
    print(f"Contents:\n{creds}")

# If file missing, search more
print("\n=== Searching all of /etc for creds ===")
stdin, stdout, stderr = ssh.exec_command("sudo find /etc -type f -exec grep -l 'morgan' {} \\; 2>/dev/null | head -10")
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))

# Check if mounted via autofs or manually
print("\n=== Check autofs ===")
stdin, stdout, stderr = ssh.exec_command("systemctl status autofs 2>/dev/null || echo 'No autofs'")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
