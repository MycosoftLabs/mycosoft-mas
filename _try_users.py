import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Trying different usernames and passwords...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Try with different credential combinations
attempts = [
    ("mycosoft", "REDACTED_VM_SSH_PASSWORD"),
    ("admin", "REDACTED_VM_SSH_PASSWORD"),
    ("morgan", "Mushroom1!"),
    ("morgan", "mushroom1"),
    ("mycosoft", "Mushroom1!"),
]

for username, password in attempts:
    print(f"\nTrying: username={username}")
    # Write creds
    cmd = f'''
sudo bash -c 'cat > /etc/samba/mycosoft-nas.creds << "CREDEOF"
username={username}
password={password}
CREDEOF'
sudo chmod 600 /etc/samba/mycosoft-nas.creds
sudo umount /mnt/mycosoft-nas 2>/dev/null || true
sudo mount -t cifs //192.168.0.105/mycosoft.com /mnt/mycosoft-nas -o credentials=/etc/samba/mycosoft-nas.creds,vers=3.0,uid=1000,gid=1000 2>&1
if mountpoint -q /mnt/mycosoft-nas; then
    echo "SUCCESS with {username}!"
    ls /mnt/mycosoft-nas/ | head -5
    exit 0
fi
'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(8)
    result = stdout.read().decode('utf-8', errors='replace')
    print(result)
    if "SUCCESS" in result:
        break

ssh.close()
