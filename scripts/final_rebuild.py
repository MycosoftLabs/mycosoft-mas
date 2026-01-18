import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run_cmd(ssh, cmd, timeout=60):
    print(f'> {cmd[:80]}...' if len(cmd) > 80 else f'> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip())
    return exit_code, output

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== FINAL REBUILD WITH CORRECT SUPABASE URL ===\n')

print('[1] Verify Dockerfile has real Supabase URL:')
_, out = run_cmd(ssh, 'grep "kzwnthsxofkkdxcmqbcl" /opt/mycosoft/website/Dockerfile')
if 'kzwnthsxofkkdxcmqbcl' not in out:
    print('ERROR: Real Supabase URL not in Dockerfile!')
    ssh.close()
    sys.exit(1)

print('\n[2] Rebuilding Docker image (will take 3-4 minutes with cache)...')
channel = ssh.get_transport().open_session()
channel.settimeout(600)
channel.exec_command(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1')

while True:
    if channel.recv_ready():
        data = channel.recv(4096).decode('utf-8', errors='replace')
        for line in data.split('\n'):
            line = line.strip()
            if line and any(x in line.lower() for x in ['done', 'success', 'error', 'failed', 'exporting', 'step']):
                print(line[:120])
    if channel.exit_status_ready():
        while channel.recv_ready():
            print(channel.recv(4096).decode('utf-8', errors='replace'), end='')
        break
    time.sleep(0.1)

exit_code = channel.recv_exit_status()
print(f'\nBuild exit code: {exit_code}')

if exit_code == 0:
    print('\n[3] Stop and remove old container:')
    run_cmd(ssh, f'echo "{VM_PASS}" | sudo -S docker stop mycosoft-website 2>/dev/null || true')
    run_cmd(ssh, f'echo "{VM_PASS}" | sudo -S docker rm mycosoft-website 2>/dev/null || true')
    
    print('\n[4] Start new container:')
    run_cmd(ssh, f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
    
    print('\n[5] Wait 30 seconds...')
    time.sleep(30)
    
    print('\n[6] Container status:')
    run_cmd(ssh, 'docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"')
    
    print('\n[7] Test for real Supabase URL in page:')
    _, out = run_cmd(ssh, "curl -s http://localhost:3000/login | grep -o 'kzwnthsxofkkdxcmqbcl' | head -1")
    if 'kzwnthsxofkkdxcmqbcl' in out:
        print('SUCCESS: Real Supabase URL found!')
    else:
        print('WARNING: Real Supabase URL not found')
        run_cmd(ssh, "curl -s http://localhost:3000/login | grep -o 'supabase' | head -1")
    
    print('\n[8] OAuth buttons:')
    run_cmd(ssh, "curl -s http://localhost:3000/login | grep -io 'continue with google\\|continue with github'")
    
    print('\n=== DONE - Clear Cloudflare cache! ===')
else:
    print('\n=== BUILD FAILED ===')

ssh.close()
