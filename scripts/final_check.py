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
_, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}\t{{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CURL TEST ===')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/')
print(f'Homepage: {out.read().decode("utf-8", errors="replace")}')

print('\n=== RECENT LOGS ===')
_, out, _ = ssh.exec_command('docker logs mycosoft-website --tail 20 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== RESTART CLOUDFLARE TUNNEL ===')
_, out, err = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl restart cloudflared 2>&1')
out.channel.recv_exit_status()
print('Restarted cloudflared service')

import time
time.sleep(5)

print('\n=== CLOUDFLARE STATUS ===')
_, out, _ = ssh.exec_command('systemctl status cloudflared --no-pager 2>&1 | head -15')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
