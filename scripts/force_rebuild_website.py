#!/usr/bin/env python3
"""Force rebuild website on VM 103 via SSH/Paramiko"""
import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'
WEBSITE_PATH = '/opt/mycosoft/website'

def main():
    print('=' * 60)
    print('  FORCE REBUILDING WEBSITE FROM SOURCE (SSH/Paramiko)')
    print('=' * 60)
    print(f'\nConnecting to {VM_HOST}...')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    print('Connected!')
    
    print('\n[1] Pulling latest code from GitHub...')
    _, out, err = ssh.exec_command(f'cd {WEBSITE_PATH} && git fetch origin && git reset --hard origin/main 2>&1')
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[2] Current Docker images:')
    _, out, _ = ssh.exec_command('docker images | grep -E "website|REPOSITORY"')
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[3] Building website image ONLY (this takes 5-10 minutes)...')
    # Build only the website service using docker compose build, not full "up"
    _, out, err = ssh.exec_command(
        f'cd {WEBSITE_PATH} && echo "{VM_PASS}" | sudo -S docker compose build --no-cache website 2>&1',
        timeout=900  # 15 minute timeout for build
    )
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    print(f'Build exit code: {exit_code}')
    lines = output.strip().split('\n')
    print('\n'.join(lines[-50:]))
    
    if exit_code != 0:
        print('\n!!! BUILD FAILED !!!')
        ssh.close()
        return 1
    
    print('\n[4] Stopping old container...')
    _, out, _ = ssh.exec_command(
        f'echo "{VM_PASS}" | sudo -S docker stop website-website-1 2>/dev/null || true; '
        f'echo "{VM_PASS}" | sudo -S docker rm website-website-1 2>/dev/null || true; '
        f'echo "{VM_PASS}" | sudo -S docker stop mycosoft-website 2>/dev/null || true; '
        f'echo "{VM_PASS}" | sudo -S docker rm mycosoft-website 2>/dev/null || true'
    )
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace') or 'Done')
    
    print('\n[5] Starting website container ONLY...')
    _, out, _ = ssh.exec_command(
        f'cd {WEBSITE_PATH} && echo "{VM_PASS}" | sudo -S docker compose up -d website 2>&1'
    )
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[6] Waiting 25 seconds for startup...')
    time.sleep(25)
    
    print('\n[7] Container status:')
    _, out, _ = ssh.exec_command('docker ps --filter name=website --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[8] Container logs (last 10 lines):')
    _, out, _ = ssh.exec_command('docker logs website-website-1 --tail 10 2>&1')
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[9] Testing localhost:3000...')
    _, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000')
    status = out.read().decode('utf-8', errors='replace').strip()
    print(f'HTTP Status: {status}')
    
    print('\n[10] Testing /devices/mushroom-1...')
    _, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/devices/mushroom-1')
    status = out.read().decode('utf-8', errors='replace').strip()
    print(f'HTTP Status: {status}')
    
    ssh.close()
    
    print('\n' + '=' * 60)
    print('  DEPLOYMENT COMPLETE!')
    print('=' * 60)
    print('\nNext steps:')
    print('1. Clear Cloudflare cache (PURGE EVERYTHING)')
    print('2. Test: https://sandbox.mycosoft.com/devices/mushroom-1')
    return 0

if __name__ == '__main__':
    sys.exit(main())
