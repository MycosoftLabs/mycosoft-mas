import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== VM WEBSITE CODE VERSION ===')
print('\n[1] Current Git Commit on VM:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git log --oneline -5 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('[2] Check if login page exists:')
_, out, _ = ssh.exec_command('ls -la /opt/mycosoft/website/app/login/ 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('[3] Check login page content (first 50 lines):')
_, out, _ = ssh.exec_command('head -50 /opt/mycosoft/website/app/login/page.tsx 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('[4] Check if Supabase auth hook exists:')
_, out, _ = ssh.exec_command('ls -la /opt/mycosoft/website/hooks/use-supabase-auth.ts 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('[5] Git remote URL:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git remote -v 2>&1')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
