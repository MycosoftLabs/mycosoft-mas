import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CONTAINER STATUS ===')
_, out, _ = ssh.exec_command('docker ps -a --filter name=mycosoft-website --format "{{.Names}}\t{{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('=== LAST 50 LOGS ===')
_, out, _ = ssh.exec_command('docker logs mycosoft-website --tail 50 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('=== PORT 3000 CHECK ===')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "FAILED"')
print(out.read().decode('utf-8', errors='replace'))

print('=== CLOUDFLARE TUNNEL STATUS ===')
_, out, _ = ssh.exec_command('docker ps --filter name=cloudflared --format "{{.Names}}\t{{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
