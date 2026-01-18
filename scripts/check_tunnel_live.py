import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CURRENT TUNNEL LOGS ===')
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 50 --no-pager 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== TEST CURL TO TUNNEL SERVICE URL ===')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/')
print(f'127.0.0.1:3000 returns: {out.read().decode("utf-8", errors="replace")}')

print('\n=== CHECKING IF TUNNEL CAN REACH WEBSITE ===')
_, out, _ = ssh.exec_command('curl -s -H "Host: sandbox.mycosoft.com" http://localhost:3000/ | head -5')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CLOUDFLARED CONFIG ===')
_, out, _ = ssh.exec_command('cat /etc/systemd/system/cloudflared.service 2>&1')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
