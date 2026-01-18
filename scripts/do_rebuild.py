import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=60)

print('=== REBUILDING DOCKER IMAGE FROM SOURCE ===')
print('This will take 5-10 minutes...\n')

# Run docker build with extended timeout
channel = ssh.get_transport().open_session()
channel.settimeout(900)  # 15 minute timeout
channel.exec_command(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1')

# Stream output
while True:
    if channel.recv_ready():
        data = channel.recv(4096).decode('utf-8', errors='replace')
        print(data, end='', flush=True)
    if channel.exit_status_ready():
        # Get remaining data
        while channel.recv_ready():
            data = channel.recv(4096).decode('utf-8', errors='replace')
            print(data, end='', flush=True)
        break
    time.sleep(0.1)

exit_code = channel.recv_exit_status()
print(f'\n\nBuild exit code: {exit_code}')

if exit_code == 0:
    print('\n=== RESTARTING CONTAINER ===')
    _, out, _ = ssh.exec_command(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\nWaiting 20 seconds for startup...')
    time.sleep(20)
    
    print('\n=== FINAL STATUS ===')
    _, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website')
    print(out.read().decode('utf-8', errors='replace'))
    
    _, out, _ = ssh.exec_command('docker images | grep website | head -3')
    print(out.read().decode('utf-8', errors='replace'))

ssh.close()
print('\n=== DONE - Clear Cloudflare cache now! ===')
