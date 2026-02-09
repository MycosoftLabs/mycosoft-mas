import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Creating mindex directory on NAS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Try creating directory
cmd = '''
echo "=== Current permissions ==="
ls -la /mnt/mycosoft-nas/

echo ""
echo "=== Trying to create mindex ==="
mkdir /mnt/mycosoft-nas/mindex 2>&1 || echo "mkdir failed"
ls -la /mnt/mycosoft-nas/

echo ""
echo "=== Check write permissions ==="
touch /mnt/mycosoft-nas/test_write.txt 2>&1 && echo "Write OK" && rm /mnt/mycosoft-nas/test_write.txt
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

ssh.close()
