import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Get credentials from sandbox
sandbox_host = "192.168.0.187"
sandbox_user = "mycosoft"
sandbox_pass = "REDACTED_VM_SSH_PASSWORD"

print("Getting NAS credentials from Sandbox...")
ssh_sandbox = paramiko.SSHClient()
ssh_sandbox.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_sandbox.connect(sandbox_host, username=sandbox_user, password=sandbox_pass, timeout=15)

# Get full credentials
stdin, stdout, stderr = ssh_sandbox.exec_command("sudo cat /etc/samba/mycosoft-nas.creds")
time.sleep(2)
nas_creds = stdout.read().decode('utf-8', errors='replace').strip()
print(f"Got credentials ({len(nas_creds)} chars)")

# Create mindex directories on NAS
print("\n=== Creating MINDEX directories on NAS ===")
stdin, stdout, stderr = ssh_sandbox.exec_command("""
sudo mkdir -p /mnt/mycosoft-nas/mindex/ledger
sudo mkdir -p /mnt/mycosoft-nas/mindex/backups
sudo mkdir -p /mnt/mycosoft-nas/mindex/snapshots
sudo mkdir -p /mnt/mycosoft-nas/mindex/data
sudo chown -R mycosoft:mycosoft /mnt/mycosoft-nas/mindex
ls -la /mnt/mycosoft-nas/
ls -la /mnt/mycosoft-nas/mindex/
""")
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

ssh_sandbox.close()

# Now configure MINDEX VM
print("\n=== Configuring MINDEX VM with NAS mount ===")
mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "REDACTED_VM_SSH_PASSWORD"

ssh_mindex = paramiko.SSHClient()
ssh_mindex.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_mindex.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected to MINDEX VM!")

# Create credentials file and mount
setup_cmd = f'''
# Create directories
sudo mkdir -p /mnt/mycosoft-nas
sudo mkdir -p /etc/samba

# Create credentials file
echo '{nas_creds}' | sudo tee /etc/samba/mycosoft-nas.creds > /dev/null
sudo chmod 600 /etc/samba/mycosoft-nas.creds

# Add to fstab
if ! grep -q "mycosoft-nas" /etc/fstab; then
    echo "//192.168.0.105/mycosoft.com /mnt/mycosoft-nas cifs credentials=/etc/samba/mycosoft-nas.creds,vers=3.0,iocharset=utf8,uid=1000,gid=1000,file_mode=0644,dir_mode=0755,nofail,_netdev 0 0" | sudo tee -a /etc/fstab
fi

# Mount
sudo mount -a

# Verify
if mountpoint -q /mnt/mycosoft-nas; then
    echo "SUCCESS: NAS mounted!"
    ls -la /mnt/mycosoft-nas/
else
    echo "Mount failed - trying direct mount..."
    sudo mount -t cifs //192.168.0.105/mycosoft.com /mnt/mycosoft-nas -o credentials=/etc/samba/mycosoft-nas.creds,vers=3.0
    ls -la /mnt/mycosoft-nas/
fi
'''

stdin, stdout, stderr = ssh_mindex.exec_command(setup_cmd)
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print(f"Errors: {err}")

ssh_mindex.close()
print("NAS setup complete!")
