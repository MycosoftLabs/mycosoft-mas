import paramiko
import os
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = os.environ.get("VM_PASSWORD", "")

print("Installing NFS with proper sudo...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Use sudo with password via stdin
install_cmd = '''
echo '<VM_PASSWORD>' | sudo -S apt-get update -qq 2>/dev/null
echo '<VM_PASSWORD>' | sudo -S apt-get install -y nfs-kernel-server 2>/dev/null

# Create exports file
echo '<VM_PASSWORD>' | sudo -S bash -c 'echo "/mnt/mycosoft-nas 192.168.0.189(rw,sync,no_subtree_check,no_root_squash,crossmnt)" > /etc/exports'

# Export and restart
echo '<VM_PASSWORD>' | sudo -S exportfs -ra 2>/dev/null
echo '<VM_PASSWORD>' | sudo -S systemctl restart nfs-kernel-server 2>/dev/null
sleep 3

# Check
echo '<VM_PASSWORD>' | sudo -S systemctl status nfs-kernel-server 2>/dev/null | head -5
echo ""
echo '<VM_PASSWORD>' | sudo -S exportfs -v 2>/dev/null
'''

stdin, stdout, stderr = ssh.exec_command(install_cmd)
time.sleep(60)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
