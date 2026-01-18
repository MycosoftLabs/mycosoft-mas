#!/usr/bin/env python3
"""Expand LVM and deploy website - STANDALONE SCRIPT"""
import paramiko
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

print('=' * 60)
print('  EXPAND LVM + DEPLOY WEBSITE')
print('=' * 60)

print(f'\nConnecting to {VM_HOST}...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
print('Connected!')

def run(cmd, timeout=600):
    print(f'\n>>> {cmd[:70]}...')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if len(output) > 3000:
        print(output[-3000:])
    else:
        print(output)
    return code, output

# Step 1: Current disk
print('\n' + '=' * 40)
print('[1] CURRENT DISK SPACE')
print('=' * 40)
run('df -h /')
run('lsblk')

# Step 2: Expand LVM
print('\n' + '=' * 40)
print('[2] EXPANDING LVM PARTITION')
print('=' * 40)
run(f'echo "{VM_PASS}" | sudo -S growpart /dev/sda 3 2>&1 || echo "Already at max"')
run(f'echo "{VM_PASS}" | sudo -S pvresize /dev/sda3 2>&1')
run(f'echo "{VM_PASS}" | sudo -S lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv 2>&1 || echo "Already extended"')
run(f'echo "{VM_PASS}" | sudo -S resize2fs /dev/ubuntu-vg/ubuntu-lv 2>&1')

print('\nNew disk space:')
run('df -h /')

# Step 3: Docker cleanup
print('\n' + '=' * 40)
print('[3] DOCKER CLEANUP')
print('=' * 40)
run(f'echo "{VM_PASS}" | sudo -S docker system prune -af 2>&1 | tail -10')

# Step 4: Pull code
print('\n' + '=' * 40)
print('[4] PULLING LATEST CODE')
print('=' * 40)
run('cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1')

# Step 5: Build
print('\n' + '=' * 40)
print('[5] BUILDING DOCKER IMAGE (5-10 min)')
print('=' * 40)
code, _ = run(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1', timeout=900)
if code != 0:
    print('\n!!! BUILD FAILED !!!')
    ssh.close()
    sys.exit(1)

# Step 6: Restart container
print('\n' + '=' * 40)
print('[6] RESTARTING CONTAINER')
print('=' * 40)
run(f'echo "{VM_PASS}" | sudo -S docker stop mycosoft-website 2>/dev/null || true')
run(f'echo "{VM_PASS}" | sudo -S docker rm mycosoft-website 2>/dev/null || true')
run(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')

print('\nWaiting 30s for startup...')
time.sleep(30)

# Step 7: Verify
print('\n' + '=' * 40)
print('[7] VERIFICATION')
print('=' * 40)
run('docker ps --format "table {{.Names}}\t{{.Status}}"')
run('df -h /')
run('free -h')
run('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000')

# Step 8: Restart cloudflared
print('\n' + '=' * 40)
print('[8] CLOUDFLARED')
print('=' * 40)
run(f'echo "{VM_PASS}" | sudo -S systemctl restart cloudflared 2>&1')
run(f'echo "{VM_PASS}" | sudo -S systemctl status cloudflared 2>&1 | head -5')

ssh.close()

print('\n' + '=' * 60)
print('  COMPLETE!')
print('=' * 60)
print('\nNow:')
print('1. Clear Cloudflare cache')
print('2. Test https://sandbox.mycosoft.com/login?redirectTo=%2Fdashboard%2Fcrep')
