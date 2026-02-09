import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Using sudo for SSHFS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
# Create new mount point
sudo umount /mnt/mycosoft-nas 2>/dev/null || true  
sudo rm -rf /mnt/mycosoft-nas
sudo mkdir -p /mnt/nas-share
sudo chown mycosoft:mycosoft /mnt/nas-share

# Try SSHFS with debug
echo "=== Testing SSH connectivity ==="
sshpass -p 'REDACTED_VM_SSH_PASSWORD' ssh -o StrictHostKeyChecking=no mycosoft@192.168.0.187 "ls /mnt/mycosoft-nas/" 2>&1

echo ""
echo "=== Mounting with SSHFS ==="
sshpass -p 'REDACTED_VM_SSH_PASSWORD' sshfs -o StrictHostKeyChecking=no,reconnect,ServerAliveInterval=15 mycosoft@192.168.0.187:/mnt/mycosoft-nas /mnt/nas-share
echo "Exit: $?"

echo ""
mount | grep fuse
ls -la /mnt/nas-share/
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(15)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print(f"Stderr: {err}")

ssh.close()
