import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Setting up cron sync and checking services...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
# Setup cron for hourly sync
(crontab -l 2>/dev/null | grep -v sync_to_nas; echo "0 * * * * /opt/mycosoft/sync_to_nas.sh >> /var/log/nas_sync.log 2>&1") | crontab -

echo "=== Cron jobs ==="
crontab -l

echo ""
echo "=== Running first sync ==="
/opt/mycosoft/sync_to_nas.sh

echo ""
echo "=== Docker containers ==="
docker ps -a

echo ""
echo "=== Checking Dream Machine connectivity ==="
ping -c 2 192.168.0.1 2>&1 | head -5
nc -zv 192.168.0.1 22 2>&1 || echo "SSH not available on Dream Machine"
nc -zv 192.168.0.1 443 2>&1 || echo "HTTPS available"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(30)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
