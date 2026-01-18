import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run_cmd(ssh, cmd, timeout=60):
    print(f'> {cmd[:100]}...' if len(cmd) > 100 else f'> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip())
    return exit_code, output

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== FORCE PULLING LATEST CODE ===\n')
run_cmd(ssh, 'cd /opt/mycosoft/website && git fetch --all')
run_cmd(ssh, 'cd /opt/mycosoft/website && git reset --hard origin/main')
run_cmd(ssh, 'cd /opt/mycosoft/website && git log --oneline -1')

print('\n=== CHECK DOCKERFILE ===')
run_cmd(ssh, 'grep -A 3 "STRIPE_SECRET_KEY" /opt/mycosoft/website/Dockerfile || echo "STRIPE_SECRET_KEY not found"')

print('\n=== BUILDING... ===\n')
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
                if len(last_lines) > 50:
                    last_lines.pop(0)
                if any(x in line.lower() for x in ['error', 'warn', 'done', 'success', 'failed']):
                    print(line[:150])
    if channel.exit_status_ready():
        while channel.recv_ready():
            data = channel.recv(4096).decode('utf-8', errors='replace')
            print(data, end='')
        break
    time.sleep(0.1)

exit_code = channel.recv_exit_status()
print(f'\nBuild exit code: {exit_code}')

if exit_code != 0:
    print('\n=== LAST 20 LINES ===')
    for line in last_lines[-20:]:
        print(line[:150])

if exit_code == 0:
    print('\n=== RESTARTING CONTAINER ===\n')
    run_cmd(ssh, f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website')
    time.sleep(30)
    print('\n=== VERIFYING ===\n')
    run_cmd(ssh, 'docker ps --filter name=mycosoft-website')
    print('\nChecking for OAuth:')
    run_cmd(ssh, "curl -s http://localhost:3000/login | grep -io 'continue with google\\|continue with github' | head -2")
    print('\n=== SUCCESS ===')

ssh.close()
