import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run_cmd(ssh, cmd, timeout=60):
    print(f'> {cmd[:80]}...' if len(cmd) > 80 else f'> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    errors = err.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip())
    if errors.strip():
        print(f'STDERR: {errors.strip()}')
    return exit_code, output

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== PULLING LATEST CODE ===\n')
run_cmd(ssh, 'cd /opt/mycosoft/website && git fetch origin main && git reset --hard origin/main')
run_cmd(ssh, 'cd /opt/mycosoft/website && git log --oneline -1')

print('\n=== BUILDING DOCKER IMAGE (5-10 min) ===\n')
print('Starting build...')

# Build with streaming output
channel = ssh.get_transport().open_session()
channel.settimeout(900)
channel.exec_command(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1')

build_success = False
while True:
    if channel.recv_ready():
        data = channel.recv(4096).decode('utf-8', errors='replace')
        for line in data.split('\n'):
            line = line.strip()
            if line:
                # Only print important lines
                if any(x in line.lower() for x in ['#', 'step', 'done', 'error', 'warning', 'success', 'failed', 'build']):
                    print(line[:120])
    if channel.exit_status_ready():
        while channel.recv_ready():
            print(channel.recv(4096).decode('utf-8', errors='replace'), end='')
        break
    time.sleep(0.1)

exit_code = channel.recv_exit_status()
print(f'\nBuild exit code: {exit_code}')
build_success = exit_code == 0

if build_success:
    print('\n=== RESTARTING CONTAINER ===\n')
    run_cmd(ssh, f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website')
    
    print('\nWaiting 30 seconds...')
    time.sleep(30)
    
    print('\n=== VERIFYING ===\n')
    run_cmd(ssh, 'docker ps --filter name=mycosoft-website')
    
    print('\nChecking for OAuth in login page:')
    _, out = run_cmd(ssh, "curl -s http://localhost:3000/login | grep -io 'continue with google\\|continue with github'")
    
    print('\n=== DONE - CLEAR CLOUDFLARE CACHE ===')
else:
    print('\n=== BUILD FAILED ===')

ssh.close()
