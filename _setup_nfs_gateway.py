import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Setting up NFS re-export on Sandbox for MINDEX access...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Create NFS export from sandbox
setup_cmd = '''
# Install NFS server
sudo apt-get update -qq
sudo apt-get install -y nfs-kernel-server

# Create export entry for the NAS mount
echo "/mnt/mycosoft-nas 192.168.0.189(rw,sync,no_subtree_check,no_root_squash,crossmnt)" | sudo tee /etc/exports

# Export
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server

# Verify
sudo exportfs -v
echo ""
echo "NFS server status:"
systemctl is-active nfs-kernel-server
'''

stdin, stdout, stderr = ssh.exec_command(setup_cmd)
time.sleep(60)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err and "error" in err.lower():
    print(f"Errors: {err}")

ssh.close()
print("\nNFS gateway setup complete!")
