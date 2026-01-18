import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== WEBSITE CONTAINER HEALTH ===')
_, out, _ = ssh.exec_command('docker inspect mycosoft-website --format "{{json .State.Health}}" 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== FULL WEBSITE LOGS ===')
_, out, _ = ssh.exec_command('docker logs mycosoft-website 2>&1 | tail -100')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CURL TEST FROM VM ===')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/')
print(f'Homepage: {out.read().decode("utf-8", errors="replace")}')

_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/natureos/devices')
print(f'Devices page: {out.read().decode("utf-8", errors="replace")}')

_, out, _ = ssh.exec_command('curl -s http://localhost:3000/api/health')
print(f'Health API: {out.read().decode("utf-8", errors="replace")}')

print('\n=== RESTART WEBSITE CONTAINER ===')
_, out, err = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S docker restart mycosoft-website 2>&1')
out.channel.recv_exit_status()
print(out.read().decode('utf-8', errors='replace'))
print(err.read().decode('utf-8', errors='replace'))

print('\n=== WAIT 10 SECONDS ===')
import time
time.sleep(10)

print('\n=== CHECK AFTER RESTART ===')
_, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}\t{{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/')
print(f'Homepage after restart: {out.read().decode("utf-8", errors="replace")}')

ssh.close()
print('\n=== DONE ===')
