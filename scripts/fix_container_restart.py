#!/usr/bin/env python3
"""Fix container conflict and restart properly"""
import paramiko
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

print('Connecting...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
print('Connected!')

def run(cmd):
    print(f'>>> {cmd}')
    _, out, _ = ssh.exec_command(cmd, timeout=120)
    out.channel.recv_exit_status()
    print(out.read().decode('utf-8', errors='replace'))

print('\n[1] Stop all website containers:')
run(f"echo '{VM_PASS}' | sudo -S docker ps -a --filter name=website --format '{{{{.ID}}}}' | xargs -r docker stop 2>/dev/null || true")

print('\n[2] Remove all website containers:')
run(f"echo '{VM_PASS}' | sudo -S docker ps -a --filter name=website --format '{{{{.ID}}}}' | xargs -r docker rm -f 2>/dev/null || true")

print('\n[3] Start fresh container:')
run(f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1")

print('\n[4] Wait 20s...')
time.sleep(20)

print('\n[5] Container status:')
run('docker ps --filter name=mycosoft --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')

print('\n[6] Test endpoint:')
run('curl -s -o /dev/null -w "HTTP: %{http_code}" http://localhost:3000')

print('\n[7] Restart cloudflared:')
run(f"echo '{VM_PASS}' | sudo -S systemctl restart cloudflared 2>&1")
run(f"echo '{VM_PASS}' | sudo -S systemctl status cloudflared 2>&1 | head -5")

ssh.close()
print('\n=== DONE ===')
print('Clear Cloudflare cache and test!')
