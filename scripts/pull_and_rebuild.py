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

print('=== PULLING LATEST CODE AND REBUILDING ===')

print('\n[1] Pulling latest code...')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git pull origin main 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[2] Current commit:')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git log --oneline -1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[3] Starting Docker build (this takes ~2-3 minutes)...')
_, out, err = ssh.exec_command('cd /opt/mycosoft/website && docker build -t website-website:latest . 2>&1', timeout=600)
exit_code = out.channel.recv_exit_status()
output = out.read().decode('utf-8', errors='replace')
print(f'\nBuild exit code: {exit_code}')

# Print last 40 lines
lines = output.strip().split('\n')
print('\nLast 40 lines of build output:')
print('\n'.join(lines[-40:]))

if exit_code == 0:
    print('\n[4] Build successful! Restarting container...')
    _, out, _ = ssh.exec_command(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[5] Waiting for startup...')
    time.sleep(20)
    
    print('\n[6] Container status:')
    _, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"')
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[7] New image timestamp:')
    _, out, _ = ssh.exec_command('docker images | grep website')
    print(out.read().decode('utf-8', errors='replace'))
else:
    print('\nBuild FAILED - check output above for errors')

ssh.close()
print('\n=== DONE ===')
