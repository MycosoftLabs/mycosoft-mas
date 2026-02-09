import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Mounting NAS with proper password escaping...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Create properly formatted credentials file
print("=== Creating credentials file ===")
# The ! character needs to be in single quotes in bash, or escaped properly
# Using base64 to avoid escaping issues
setup_cmd = '''
# Create credentials file with proper escaping
sudo mkdir -p /etc/samba
sudo bash -c 'cat > /etc/samba/mycosoft-nas.creds << "CREDEOF"
username=morgan
password=REDACTED_VM_SSH_PASSWORD
domain=WORKGROUP
CREDEOF'
sudo chmod 600 /etc/samba/mycosoft-nas.creds

echo "Credentials file contents:"
sudo cat /etc/samba/mycosoft-nas.creds

# Try mount with credentials file instead of inline password
sudo umount /mnt/mycosoft-nas 2>/dev/null || true
sudo mkdir -p /mnt/mycosoft-nas

echo ""
echo "=== Attempting mount with credentials file ==="
sudo mount -t cifs //192.168.0.105/mycosoft.com /mnt/mycosoft-nas -o credentials=/etc/samba/mycosoft-nas.creds,vers=3.0,uid=1000,gid=1000,sec=ntlmssp

if mountpoint -q /mnt/mycosoft-nas; then
    echo "SUCCESS!"
    ls -la /mnt/mycosoft-nas/ | head -20
else
    echo "Failed - checking dmesg"
    dmesg | grep -i cifs | tail -5
fi
'''

stdin, stdout, stderr = ssh.exec_command(setup_cmd)
time.sleep(15)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print(f"Errors: {err}")

ssh.close()
