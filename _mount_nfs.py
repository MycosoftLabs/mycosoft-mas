import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Mounting NAS via NFS gateway on MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Mount NFS from sandbox
mount_cmd = '''
# Install NFS client
sudo apt-get install -y nfs-common -qq

# Create mount point
sudo mkdir -p /mnt/mycosoft-nas

# Remove old fstab entry
sudo sed -i '/mycosoft-nas/d' /etc/fstab

# Add NFS mount entry (via sandbox gateway)
echo "192.168.0.187:/mnt/mycosoft-nas /mnt/mycosoft-nas nfs rw,sync,hard,intr,nofail,_netdev 0 0" | sudo tee -a /etc/fstab

# Mount
sudo mount -a
sleep 2

# Verify
echo "=== Mount status ==="
mount | grep mycosoft
echo ""
echo "=== Contents ==="
ls -la /mnt/mycosoft-nas/ | head -20
'''

stdin, stdout, stderr = ssh.exec_command(mount_cmd)
time.sleep(30)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err and "error" in err.lower():
    print(f"Errors: {err}")

ssh.close()
