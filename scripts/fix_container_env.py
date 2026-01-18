import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CHECKING CONTAINER ENV CONFIG ===')

print('\n[1] Check docker-compose.yml for mycosoft-website:')
_, out, _ = ssh.exec_command('grep -A 30 "mycosoft-website:" /opt/mycosoft/docker-compose.yml 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[2] Check if there is an env_file or environment section:')
_, out, _ = ssh.exec_command('grep -E "env_file|environment" /opt/mycosoft/docker-compose.yml 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[3] Check /opt/mycosoft/.env for website vars:')
_, out, _ = ssh.exec_command('cat /opt/mycosoft/.env 2>&1 | head -50')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
