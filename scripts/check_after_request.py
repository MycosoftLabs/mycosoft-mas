import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Check current state
print('=== WAITING FOR REQUEST TO COME THROUGH ===')
print('Check latest logs after a browser request...')
time.sleep(2)

print('\n=== LATEST TUNNEL LOGS AFTER REQUEST ===')
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 10 --no-pager 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK WEBSITE LOGS AFTER REQUEST ===')
_, out, _ = ssh.exec_command('docker logs mycosoft-website --tail 10 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CURRENT TIME ON VM ===')
_, out, _ = ssh.exec_command('date')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== TEST DIRECT CURL FROM VM ===')
_, out, _ = ssh.exec_command('curl -s -I http://localhost:3000/ 2>&1 | head -10')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
