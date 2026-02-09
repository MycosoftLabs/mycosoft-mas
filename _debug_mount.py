import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Check dmesg for actual error
print("=== Recent CIFS errors in dmesg ===")
stdin, stdout, stderr = ssh.exec_command("sudo dmesg | grep -i cifs | tail -20")
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Check current credentials file
print("\n=== Credentials file ===")
stdin, stdout, stderr = ssh.exec_command("sudo cat /etc/samba/mycosoft-nas.creds")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Try manual mount with direct credentials
print("\n=== Trying manual mount ===")
# The password contains ! which needs escaping
mount_cmd = '''
sudo umount /mnt/mycosoft-nas 2>/dev/null || true
sudo mount -t cifs //192.168.0.105/mycosoft.com /mnt/mycosoft-nas -o username=morgan,password='REDACTED_VM_SSH_PASSWORD',vers=3.0,uid=1000,gid=1000
echo "Exit code: $?"
mount | grep cifs
'''
stdin, stdout, stderr = ssh.exec_command(mount_cmd)
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

ssh.close()
