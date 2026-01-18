import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CLOUDFLARE TUNNEL LOGS (last 30 lines) ===')
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 30 --no-pager')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== TEST CURL TO LOCALHOST:3000 ===')
_, out, _ = ssh.exec_command('curl -v http://localhost:3000/ 2>&1 | head -30')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== NETSTAT FOR PORT 3000 ===')
_, out, _ = ssh.exec_command('netstat -tlnp 2>/dev/null | grep 3000')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== DOCKER PORT MAPPING ===')
_, out, _ = ssh.exec_command('docker port mycosoft-website')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== DOCKER INSPECT PORTS ===')
_, out, _ = ssh.exec_command('docker inspect mycosoft-website --format "{{json .NetworkSettings.Ports}}"')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
