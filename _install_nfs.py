import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Installing NFS with proper sudo...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Use sudo with password via stdin
install_cmd = '''
echo 'Mushroom1!Mushroom1!' | sudo -S apt-get update -qq 2>/dev/null
echo 'Mushroom1!Mushroom1!' | sudo -S apt-get install -y nfs-kernel-server 2>/dev/null

# Create exports file
echo 'Mushroom1!Mushroom1!' | sudo -S bash -c 'echo "/mnt/mycosoft-nas 192.168.0.189(rw,sync,no_subtree_check,no_root_squash,crossmnt)" > /etc/exports'

# Export and restart
echo 'Mushroom1!Mushroom1!' | sudo -S exportfs -ra 2>/dev/null
echo 'Mushroom1!Mushroom1!' | sudo -S systemctl restart nfs-kernel-server 2>/dev/null
sleep 3

# Check
echo 'Mushroom1!Mushroom1!' | sudo -S systemctl status nfs-kernel-server 2>/dev/null | head -5
echo ""
echo 'Mushroom1!Mushroom1!' | sudo -S exportfs -v 2>/dev/null
'''

stdin, stdout, stderr = ssh.exec_command(install_cmd)
time.sleep(60)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
