import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== FORCE FRESH REBUILD ===')

print('\n[1] Force pull latest code...')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git fetch origin main && git reset --hard origin/main 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[2] Current commit:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git log --oneline -3')
print(out.read().decode('utf-8', errors='replace'))

print('\n[3] Check stripe webhooks route:')
_, out, _ = ssh.exec_command('head -30 /opt/mycosoft/website/app/api/stripe/webhooks/route.ts')
print(out.read().decode('utf-8', errors='replace'))

print('\n[4] Clean docker cache and rebuild...')
_, out, err = ssh.exec_command('cd /opt/mycosoft/website && docker build --no-cache -t website-website:latest . 2>&1', timeout=900)
exit_code = out.channel.recv_exit_status()
output = out.read().decode('utf-8', errors='replace')
print(f'\nBuild exit code: {exit_code}')

# Print last 50 lines
lines = output.strip().split('\n')
print('\nLast 50 lines:')
print('\n'.join(lines[-50:]))

if exit_code == 0:
    print('\n[5] Build successful! Restarting...')
    _, out, _ = ssh.exec_command(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))

ssh.close()
