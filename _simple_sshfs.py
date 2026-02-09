import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Testing SSHFS with simpler options...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
# Clean mount point
sudo umount /mnt/mycosoft-nas 2>/dev/null || true
rm -rf /mnt/mycosoft-nas
mkdir -p /mnt/mycosoft-nas

# Try simple SSHFS without allow_other
echo "=== Trying simple SSHFS ==="
sshpass -p 'Mushroom1!Mushroom1!' sshfs -o StrictHostKeyChecking=no mycosoft@192.168.0.187:/mnt/mycosoft-nas /mnt/mycosoft-nas 2>&1
echo "Exit code: $?"

echo ""
echo "=== Mount result ==="
mount | grep mycosoft

echo ""
echo "=== Contents ==="
ls -la /mnt/mycosoft-nas/ || echo "Mount failed"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(15)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

ssh.close()
