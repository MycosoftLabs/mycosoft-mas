import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== COMPARING OAUTH/SUPABASE CONFIG ===')

print('\n[1] Environment variables in website container:')
_, out, _ = ssh.exec_command('docker exec mycosoft-website env | grep -i supabase 2>&1')
result = out.read().decode('utf-8', errors='replace')
print(result if result else '(no SUPABASE env vars found)')

print('\n[2] Check .env.local on VM:')
_, out, _ = ssh.exec_command('cat /opt/mycosoft/website/.env.local 2>&1 | grep -i supabase')
result = out.read().decode('utf-8', errors='replace')
print(result if result else '(no .env.local or no SUPABASE vars)')

print('\n[3] Check lib/supabase/client.ts exists:')
_, out, _ = ssh.exec_command('ls -la /opt/mycosoft/website/lib/supabase/ 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[4] Check OAuth callback route:')
_, out, _ = ssh.exec_command('ls -la /opt/mycosoft/website/app/auth/callback/ 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[5] Check Google/GitHub OAuth in login page:')
_, out, _ = ssh.exec_command('grep -n "google\\|github" /opt/mycosoft/website/app/login/page.tsx 2>&1 | head -20')
print(out.read().decode('utf-8', errors='replace'))

print('\n[6] Website container env file:')
_, out, _ = ssh.exec_command('cat /opt/mycosoft/.env 2>&1 | grep -i supabase')
result = out.read().decode('utf-8', errors='replace')
print(result if result else '(no SUPABASE vars in /opt/mycosoft/.env)')

ssh.close()
