import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== FULL SYSTEM RESET ===')

# Stop everything
print('\n[1] Stopping cloudflared...')
ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl stop cloudflared')
time.sleep(2)

print('[2] Restarting website container...')
ssh.exec_command(f'echo "{VM_PASS}" | sudo -S docker restart mycosoft-website')
time.sleep(5)

print('[3] Starting cloudflared...')
ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl start cloudflared')
time.sleep(10)

print('\n=== CHECKING STATUS ===')

print('\n[4] Website container:')
_, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('[5] Cloudflared service:')
_, out, _ = ssh.exec_command('systemctl is-active cloudflared')
print(out.read().decode('utf-8', errors='replace'))

print('[6] Port 3000:')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/')
print(out.read().decode('utf-8', errors='replace'))

print('[7] Tunnel health:')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/ready')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== WAIT 30 SECONDS FOR CLOUDFLARE SYNC ===')
time.sleep(30)

print('\n[8] Testing external access...')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://sandbox.mycosoft.com/')
result = out.read().decode('utf-8', errors='replace')
print(f'External request: {result}')

print('\n[9] Tunnel requests received:')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/metrics | grep tunnel_total_requests')
print(out.read().decode('utf-8', errors='replace'))

print('\n[10] Latest tunnel logs:')
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 15 --no-pager')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
print('\n=== DONE ===')
