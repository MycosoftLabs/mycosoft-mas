import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Creating mindex subdirectories on NAS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

cmd = '''
mkdir -p /mnt/mycosoft-nas/mindex/ledger
mkdir -p /mnt/mycosoft-nas/mindex/backups
mkdir -p /mnt/mycosoft-nas/mindex/snapshots
mkdir -p /mnt/mycosoft-nas/mindex/data

echo "=== MINDEX directories created ==="
ls -la /mnt/mycosoft-nas/mindex/
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(5)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()

# Now try mounting from MINDEX VM
print("\n=== Mounting from MINDEX VM ===")
mindex_host = "192.168.0.189"

ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd2 = '''
sudo umount /mnt/mycosoft-nas 2>/dev/null || true
sudo mount -t nfs 192.168.0.187:/mnt/mycosoft-nas /mnt/mycosoft-nas 2>&1

echo "=== Mount result ==="
mount | grep nfs

echo ""
echo "=== Contents ==="
ls -la /mnt/mycosoft-nas/
ls -la /mnt/mycosoft-nas/mindex/ 2>/dev/null || echo "No mindex access"
'''

stdin, stdout, stderr = ssh2.exec_command(cmd2)
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

ssh2.close()
