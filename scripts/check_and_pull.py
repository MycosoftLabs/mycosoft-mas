import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CHECKING VM CODE ===\n')

print('[1] Current commit on VM:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git log --oneline -1')
print(out.read().decode('utf-8', errors='replace'))

print('[2] Latest commit on origin:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git fetch origin && git log origin/main --oneline -1')
print(out.read().decode('utf-8', errors='replace'))

print('[3] Hard reset to origin/main:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git reset --hard origin/main 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('[4] Verify new commit:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git log --oneline -1')
print(out.read().decode('utf-8', errors='replace'))

print('[5] Check Dockerfile for STRIPE_SECRET_KEY:')
_, out, _ = ssh.exec_command('grep "STRIPE_SECRET_KEY" /opt/mycosoft/website/Dockerfile')
result = out.read().decode('utf-8', errors='replace')
print(result if result else 'NOT FOUND!')

print('[6] Check Dockerfile for OPENAI_API_KEY:')
_, out, _ = ssh.exec_command('grep "OPENAI_API_KEY" /opt/mycosoft/website/Dockerfile')
result = out.read().decode('utf-8', errors='replace')
print(result if result else 'NOT FOUND!')

ssh.close()
