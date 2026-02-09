import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Setting up rsync-based data sync for MINDEX...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
# Clean up broken mount
sudo umount /mnt/nas-share 2>/dev/null || true
sudo rm -rf /mnt/nas-share

# Create local data directories  
sudo mkdir -p /opt/mycosoft/data/ledger
sudo mkdir -p /opt/mycosoft/data/backups
sudo mkdir -p /opt/mycosoft/data/snapshots
sudo chown -R mycosoft:mycosoft /opt/mycosoft

# Create sync script
cat > /opt/mycosoft/sync_to_nas.sh << 'SYNCEOF'
#!/bin/bash
# Sync local data to NAS via sandbox gateway
SSHPASS='REDACTED_VM_SSH_PASSWORD'
NAS_PATH="mycosoft@192.168.0.187:/mnt/mycosoft-nas/mindex"

echo "$(date): Starting sync to NAS..."
sshpass -p "$SSHPASS" rsync -avz --delete /opt/mycosoft/data/ "$NAS_PATH/" 2>&1
echo "$(date): Sync complete"
SYNCEOF
chmod +x /opt/mycosoft/sync_to_nas.sh

# Test the sync
echo "=== Testing rsync connection ==="
sshpass -p 'REDACTED_VM_SSH_PASSWORD' ssh -o StrictHostKeyChecking=no mycosoft@192.168.0.187 "ls -la /mnt/mycosoft-nas/mindex/"

echo ""
echo "=== Local data directories ==="
ls -la /opt/mycosoft/data/

echo ""
echo "=== Sync script created ==="
cat /opt/mycosoft/sync_to_nas.sh
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(20)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err and "error" in err.lower():
    print(f"Errors: {err}")

ssh.close()
