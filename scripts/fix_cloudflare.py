import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CHECKING ALL CONTAINERS ===')
_, out, _ = ssh.exec_command('docker ps -a --format "{{.Names}}\t{{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== LOOKING FOR CLOUDFLARE TUNNEL ===')
_, out, _ = ssh.exec_command('docker ps -a | grep -i cloud')
print(out.read().decode('utf-8', errors='replace') or 'No cloudflare containers found')

print('\n=== CHECKING DOCKER COMPOSE FILES ===')
_, out, _ = ssh.exec_command('ls -la /opt/mycosoft/*.yml 2>/dev/null')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECKING FOR CLOUDFLARE IN COMPOSE ===')
_, out, _ = ssh.exec_command('grep -l cloudflare /opt/mycosoft/*.yml 2>/dev/null')
result = out.read().decode('utf-8', errors='replace')
print(result or 'No cloudflare service found in compose files')

print('\n=== CHECKING STANDALONE CLOUDFLARED ===')
_, out, _ = ssh.exec_command('which cloudflared 2>/dev/null')
print(out.read().decode('utf-8', errors='replace') or 'Not installed as standalone')

print('\n=== CHECKING SYSTEMD SERVICE ===')
_, out, _ = ssh.exec_command('systemctl status cloudflared 2>&1 | head -20')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
