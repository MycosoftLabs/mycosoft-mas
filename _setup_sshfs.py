import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Setting up SSHFS mount on MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
# Install sshfs
sudo apt-get install -y sshfs -qq

# Create SSH key for passwordless access
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa -q
fi

echo ""
echo "=== SSH key for copy to Sandbox ==="
cat ~/.ssh/id_rsa.pub

echo ""
echo "=== Trying SSHFS mount ==="
sudo mkdir -p /mnt/mycosoft-nas
sudo chown mycosoft:mycosoft /mnt/mycosoft-nas

# Try with password using sshpass
sudo apt-get install -y sshpass -qq
sshpass -p 'Mushroom1!Mushroom1!' sshfs -o StrictHostKeyChecking=no,allow_other,default_permissions mycosoft@192.168.0.187:/mnt/mycosoft-nas /mnt/mycosoft-nas 2>&1

echo ""
echo "=== Mount result ==="
mount | grep sshfs

echo ""
echo "=== Contents ==="
ls -la /mnt/mycosoft-nas/
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(45)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

ssh.close()
