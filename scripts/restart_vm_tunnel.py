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

print('=== RESTARTING VM TUNNEL ===')
ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl restart cloudflared')
time.sleep(10)

print('\n=== VM TUNNEL STATUS ===')
_, out, _ = ssh.exec_command('systemctl is-active cloudflared')
print(f'Status: {out.read().decode("utf-8", errors="replace").strip()}')

print('\n=== VM CONNECTOR ID ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/ready')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== VM IP ===')
_, out, _ = ssh.exec_command('hostname -I | cut -d" " -f1')
print(f'VM IP: {out.read().decode("utf-8", errors="replace").strip()}')

print('\n=== TEST SANDBOX NOW ===')
time.sleep(5)
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" https://sandbox.mycosoft.com/')
print(f'Sandbox response: {out.read().decode("utf-8", errors="replace")}')

print('\n=== TUNNEL REQUESTS ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/metrics | grep tunnel_total_requests')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
