import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Organizing NAS data structure...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Create NAS directory structure
cmd = '''
# Development data
mkdir -p /mnt/mycosoft-nas/dev/builds
mkdir -p /mnt/mycosoft-nas/dev/logs
mkdir -p /mnt/mycosoft-nas/dev/temp

# MINDEX production data
mkdir -p /mnt/mycosoft-nas/mindex/ledger
mkdir -p /mnt/mycosoft-nas/mindex/backups
mkdir -p /mnt/mycosoft-nas/mindex/snapshots
mkdir -p /mnt/mycosoft-nas/mindex/vectors
mkdir -p /mnt/mycosoft-nas/mindex/data

# Archives - long term cold storage
mkdir -p /mnt/mycosoft-nas/archives/2026

# Verify structure
echo "=== NAS Directory Structure ==="
ls -la /mnt/mycosoft-nas/
echo ""
echo "=== Dev directories ==="
ls -la /mnt/mycosoft-nas/dev/
echo ""
echo "=== MINDEX directories ==="
ls -la /mnt/mycosoft-nas/mindex/
echo ""
echo "=== Archives directories ==="
ls -la /mnt/mycosoft-nas/archives/
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("NAS organization complete!")
