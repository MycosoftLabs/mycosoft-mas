import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

# Supabase credentials
ENV_CONTENT = '''# SUPABASE
NEXT_PUBLIC_SUPABASE_URL=https://hnevnsxnhfibhbsipqvz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhuZXZuc3huaGZpYmhic2lwcXZ6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg2NzQ1NzEsImV4cCI6MjA4NDI1MDU3MX0.ooL4ZtASkUR4aQqpN4KfUPNcEwpbPLoGfGUkEoc4g7w
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== DEPLOYING ENVIRONMENT VARIABLES ===')

print('\n[1] Creating .env.local on VM...')
# Use sftp to write the file
sftp = ssh.open_sftp()
with sftp.file('/opt/mycosoft/website/.env.local', 'w') as f:
    f.write(ENV_CONTENT)
sftp.close()
print('Created /opt/mycosoft/website/.env.local')

print('\n[2] Verifying .env.local:')
_, out, _ = ssh.exec_command('cat /opt/mycosoft/website/.env.local')
print(out.read().decode('utf-8', errors='replace'))

print('\n[3] Rebuilding website container with new env vars...')
_, out, err = ssh.exec_command(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production build mycosoft-website --no-cache 2>&1', timeout=600)
exit_code = out.channel.recv_exit_status()
output = out.read().decode('utf-8', errors='replace')
print(f'Build exit code: {exit_code}')
# Print last 20 lines
lines = output.strip().split('\n')
print('\n'.join(lines[-20:]))

print('\n[4] Restarting website container...')
_, out, _ = ssh.exec_command(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
out.channel.recv_exit_status()
print(out.read().decode('utf-8', errors='replace'))

print('\n[5] Waiting for startup...')
time.sleep(15)

print('\n[6] Verifying env vars in container:')
_, out, _ = ssh.exec_command('docker exec mycosoft-website env | grep -i supabase 2>&1')
result = out.read().decode('utf-8', errors='replace')
print(result if result else '(still no SUPABASE vars - may need to check Dockerfile)')

print('\n[7] Container status:')
_, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('\n[8] Testing login page:')
_, out, _ = ssh.exec_command('curl -s http://localhost:3000/login | head -100')
result = out.read().decode('utf-8', errors='replace')
if 'google' in result.lower() or 'github' in result.lower():
    print('Login page contains OAuth buttons!')
else:
    print('Login page loaded (checking for OAuth...)')
    print(result[:500] if result else 'No response')

ssh.close()
print('\n=== DONE ===')
