#!/usr/bin/env python3
"""Quick rebuild after code push"""
import paramiko
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

print('Connecting...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
print('Connected!')

def run(cmd, timeout=600):
    print(f'>>> {cmd[:70]}...')
    _, out, _ = ssh.exec_command(cmd, timeout=timeout)
    code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if len(output) > 2000:
        print(output[-2000:])
    else:
        print(output)
    return code

print('\n[1] Pull latest code:')
run('cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1')

print('\n[2] Show commit:')
run('cd /opt/mycosoft/website && git log -1 --oneline')

print('\n[3] Rebuild image (5-10 min):')
code = run(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1', timeout=900)
if code != 0:
    print('BUILD FAILED!')
    ssh.close()
    sys.exit(1)

print('\n[4] Restart container:')
run(f'echo "{VM_PASS}" | sudo -S docker stop mycosoft-website 2>/dev/null || true')
run(f"echo '{VM_PASS}' | sudo -S docker ps -a --filter name=website -q | xargs -r docker rm -f 2>/dev/null || true")
run(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')

print('\n[5] Wait 25s...')
time.sleep(25)

print('\n[6] Status:')
run('docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"')
run('curl -s -o /dev/null -w "HTTP: %{http_code}" http://localhost:3000')

ssh.close()
print('\n=== DONE - Clear Cloudflare cache! ===')
