import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== WEBSITE CONTAINER STATUS ===')
_, out, _ = ssh.exec_command('docker ps -a --filter name=mycosoft-website --format "{{.Names}}\t{{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== WEBSITE CONTAINER LOGS ===')
_, out, _ = ssh.exec_command('docker logs mycosoft-website --tail 50 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK PORT 3000 ===')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>&1 || echo "FAILED"')
print(f'Port 3000: {out.read().decode("utf-8", errors="replace")}')

print('\n=== RESTART WEBSITE CONTAINER ===')
_, out, err = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S docker restart mycosoft-website 2>&1')
out.channel.recv_exit_status()
print(out.read().decode('utf-8', errors='replace'))

import time
print('\n=== WAITING 15 SECONDS FOR STARTUP ===')
time.sleep(15)

print('\n=== CHECK PORT 3000 AFTER RESTART ===')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>&1 || echo "FAILED"')
print(f'Port 3000: {out.read().decode("utf-8", errors="replace")}')

print('\n=== CONTAINER STATUS AFTER RESTART ===')
_, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}\t{{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== NEW LOGS AFTER RESTART ===')
_, out, _ = ssh.exec_command('docker logs mycosoft-website --tail 20 2>&1')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
