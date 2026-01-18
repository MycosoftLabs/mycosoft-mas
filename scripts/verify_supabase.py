import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== VERIFYING SUPABASE CONFIG ===\n')

print('[1] Current git commit:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git log --oneline -1')
print(out.read().decode('utf-8', errors='replace'))

print('[2] Check Dockerfile for Supabase URL:')
_, out, _ = ssh.exec_command('grep "NEXT_PUBLIC_SUPABASE_URL" /opt/mycosoft/website/Dockerfile')
print(out.read().decode('utf-8', errors='replace'))

print('[3] Check if placeholder in Dockerfile:')
_, out, _ = ssh.exec_command('grep "placeholder" /opt/mycosoft/website/Dockerfile')
print(out.read().decode('utf-8', errors='replace'))

print('[4] Check latest commit on GitHub:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git fetch origin main && git log origin/main --oneline -1')
print(out.read().decode('utf-8', errors='replace'))

print('[5] Force pull if needed:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git reset --hard origin/main 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('[6] Verify Dockerfile after pull:')
_, out, _ = ssh.exec_command('grep "NEXT_PUBLIC_SUPABASE_URL" /opt/mycosoft/website/Dockerfile')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
