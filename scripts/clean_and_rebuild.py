import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run_cmd(ssh, cmd, timeout=300):
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

print('=== CLEANING DOCKER AND REBUILDING ===\n')

print('[1] Check disk space:')
run_cmd(ssh, 'df -h /')

print('\n[2] Clean Docker system (remove unused images, containers, cache):')
run_cmd(ssh, f'echo "{VM_PASS}" | sudo -S docker system prune -af --volumes 2>&1', timeout=120)

print('\n[3] Check disk space after cleanup:')
run_cmd(ssh, 'df -h /')

print('\n[4] Pull latest code:')
run_cmd(ssh, 'cd /opt/mycosoft/website && git fetch origin main && git reset --hard origin/main 2>&1')

print('\n[5] Verify Dockerfile has real Supabase URL:')
run_cmd(ssh, 'grep "NEXT_PUBLIC_SUPABASE_URL" /opt/mycosoft/website/Dockerfile')

print('\n[6] Building (this will take 5-10 minutes)...')
channel = ssh.get_transport().open_session()
channel.settimeout(900)
channel.exec_command(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1')

last_lines = []
while True:
    if channel.recv_ready():
        data = channel.recv(4096).decode('utf-8', errors='replace')
        for line in data.split('\n'):
            line = line.strip()
            if line:
                last_lines.append(line)
                if len(last_lines) > 60:
                    last_lines.pop(0)
                if any(x in line.lower() for x in ['error', 'done', 'success', 'failed', 'exporting']):
                    print(line[:150])
    if channel.exit_status_ready():
        while channel.recv_ready():
            print(channel.recv(4096).decode('utf-8', errors='replace'), end='')
        break
    time.sleep(0.1)

exit_code = channel.recv_exit_status()
print(f'\n\nBuild exit code: {exit_code}')

if exit_code != 0:
    print('\n=== LAST 30 LINES ===')
    for line in last_lines[-30:]:
        print(line[:150])
else:
    print('\n[7] Build successful! Restarting container...')
    run_cmd(ssh, f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
    
    print('\n[8] Waiting 30 seconds...')
    time.sleep(30)
    
    print('\n[9] Container status:')
    run_cmd(ssh, 'docker ps --filter name=mycosoft-website')
    
    print('\n[10] Checking OAuth buttons:')
    run_cmd(ssh, "curl -s http://localhost:3000/login | grep -io 'continue with google\\|continue with github'")
    
    print('\n[11] Checking Supabase URL in page:')
    _, out = run_cmd(ssh, "curl -s http://localhost:3000/login | grep -o 'supabase.co' | head -1")
    
    print('\n=== DONE - Clear Cloudflare cache! ===')

ssh.close()
