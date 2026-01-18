import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=60)

print('=== FULL DEPLOYMENT WITH FIX ===')

print('\n[1] Pull latest code...')
_, out, err = ssh.exec_command('cd /opt/mycosoft/website && git fetch origin main && git reset --hard origin/main 2>&1')
out.channel.recv_exit_status()
print(out.read().decode('utf-8', errors='replace'))

print('\n[2] Verify new commit...')
_, out, _ = ssh.exec_command('cd /opt/mycosoft/website && git log --oneline -1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[3] Rebuilding Docker image (this takes 5+ minutes)...')
channel = ssh.get_transport().open_session()
channel.settimeout(900)
channel.exec_command(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1')

while True:
    if channel.recv_ready():
        data = channel.recv(4096).decode('utf-8', errors='replace')
        # Only print key lines to reduce output
        for line in data.split('\n'):
            if any(x in line.lower() for x in ['step', 'done', 'error', 'warn', 'success', 'build']):
                print(line)
    if channel.exit_status_ready():
        while channel.recv_ready():
            data = channel.recv(4096).decode('utf-8', errors='replace')
            print(data, end='')
        break
    time.sleep(0.1)

exit_code = channel.recv_exit_status()
print(f'\n\nBuild exit code: {exit_code}')

if exit_code == 0:
    print('\n[4] Restarting container...')
    _, out, _ = ssh.exec_command(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[5] Waiting 30 seconds for startup...')
    time.sleep(30)
    
    print('\n[6] Checking container...')
    _, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"')
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[7] Testing login page for OAuth buttons...')
    _, out, _ = ssh.exec_command("curl -s http://localhost:3000/login | grep -o 'Google\\|GitHub\\|google\\|github' | sort -u")
    result = out.read().decode('utf-8', errors='replace')
    if result:
        print(f'Found OAuth providers: {result}')
    else:
        print('No OAuth providers found in HTML')
    
    print('\n=== SUCCESS - Clear Cloudflare cache! ===')
else:
    print('\n=== BUILD FAILED - Check errors above ===')

ssh.close()
