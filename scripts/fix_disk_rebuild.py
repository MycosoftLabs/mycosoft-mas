import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run(ssh, cmd, timeout=300):
    print(f'$ {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    errors = err.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip())
    if errors.strip() and 'password' not in errors.lower():
        print(f'ERR: {errors.strip()}')
    return exit_code

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('='*60)
print('DIAGNOSING AND FIXING DISK SPACE')
print('='*60)

print('\n[1] Disk usage:')
run(ssh, 'df -h')

print('\n[2] Docker disk usage:')
run(ssh, 'docker system df')

print('\n[3] Cleaning Docker build cache, dangling images, stopped containers:')
run(ssh, f'echo "{VM_PASS}" | sudo -S docker system prune -af 2>&1')

print('\n[4] Clean buildx cache specifically:')
run(ssh, f'echo "{VM_PASS}" | sudo -S docker builder prune -af 2>&1')

print('\n[5] Disk after cleanup:')
run(ssh, 'df -h /')

print('\n[6] Pulling latest code with real Supabase URL:')
run(ssh, 'cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main')

print('\n[7] Verify Dockerfile has REAL Supabase URL (not placeholder):')
run(ssh, 'grep "kzwnthsxofkkdxcmqbcl" /opt/mycosoft/website/Dockerfile || echo "ERROR: Still has placeholder!"')

print('\n[8] Rebuilding with real Supabase URL...')
print('    (This takes 3-5 minutes)')

start = time.time()
channel = ssh.get_transport().open_session()
channel.settimeout(600)
channel.exec_command(f'cd /opt/mycosoft/website && docker build -t website-website:latest . 2>&1')

while True:
    if channel.recv_ready():
        data = channel.recv(8192).decode('utf-8', errors='replace')
        for line in data.split('\n'):
            if line.strip():
                # Only print progress markers
                if any(x in line for x in ['#', 'DONE', 'ERROR', 'exporting', 'naming']):
                    elapsed = int(time.time() - start)
                    print(f'[{elapsed}s] {line.strip()[:100]}')
    if channel.exit_status_ready():
        while channel.recv_ready():
            print(channel.recv(4096).decode('utf-8', errors='replace'), end='')
        break
    time.sleep(0.5)

exit_code = channel.recv_exit_status()
print(f'\n\nBuild exit code: {exit_code}')

if exit_code == 0:
    print('\n[9] Restarting container...')
    run(ssh, f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
    
    time.sleep(30)
    
    print('\n[10] Testing login page Supabase URL:')
    run(ssh, "curl -s http://localhost:3000/login 2>/dev/null | grep -o 'https://[^\"]*supabase.co' | head -1")
    
    print('\n[11] OAuth buttons:')
    run(ssh, "curl -s http://localhost:3000/login | grep -io 'continue with google\\|continue with github'")
    
    print('\n' + '='*60)
    print('SUCCESS - Clear Cloudflare cache and test!')
    print('='*60)
else:
    print('\nBUILD FAILED')

ssh.close()
