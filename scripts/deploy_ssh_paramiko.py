#!/usr/bin/env python3
"""Deploy website via SSH/Paramiko - NOT Proxmox API"""
import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def main():
    print('=' * 60)
    print('  WEBSITE DEPLOYMENT VIA SSH/PARAMIKO')
    print('=' * 60)
    print(f'\nConnecting to {VM_HOST}...')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    print('Connected!')
    
    print('\n[1] Pulling latest code from GitHub...')
    _, out, err = ssh.exec_command('cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1')
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[2] Current Docker images:')
    _, out, _ = ssh.exec_command('docker images | grep -E "website|REPOSITORY"')
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[3] Building new image (this takes 3-5 minutes)...')
    _, out, err = ssh.exec_command(
        f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1',
        timeout=600
    )
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    print(f'Build exit code: {exit_code}')
    lines = output.strip().split('\n')
    print('\n'.join(lines[-40:]))
    
    if exit_code != 0:
        print('\n!!! BUILD FAILED !!!')
        ssh.close()
        return 1
    
    print('\n[4] Stopping old container...')
    _, out, _ = ssh.exec_command(
        f'echo "{VM_PASS}" | sudo -S docker stop mycosoft-website 2>/dev/null || true; '
        f'echo "{VM_PASS}" | sudo -S docker rm mycosoft-website 2>/dev/null || true'
    )
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace') or 'Done')
    
    print('\n[5] Starting new container...')
    _, out, _ = ssh.exec_command(
        f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1'
    )
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[6] Waiting 20 seconds for startup...')
    time.sleep(20)
    
    print('\n[7] Container status:')
    _, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
    print(out.read().decode('utf-8', errors='replace'))
    
    print('\n[8] Testing localhost:3000...')
    _, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000')
    status = out.read().decode('utf-8', errors='replace').strip()
    print(f'HTTP Status: {status}')
    
    ssh.close()
    
    print('\n' + '=' * 60)
    print('  DEPLOYMENT COMPLETE!')
    print('=' * 60)
    print('\nNext steps:')
    print('1. Clear Cloudflare cache (PURGE EVERYTHING)')
    print('2. Test: https://sandbox.mycosoft.com/login?redirectTo=%2Fdashboard%2Fcrep')
    return 0

if __name__ == '__main__':
    sys.exit(main())
