import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== STOPPING CLOUDFLARE TUNNEL ===')
_, out, err = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl stop cloudflared 2>&1')
out.channel.recv_exit_status()
print('Stopped')
time.sleep(3)

print('\n=== STARTING CLOUDFLARE TUNNEL ===')
_, out, err = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl start cloudflared 2>&1')
out.channel.recv_exit_status()
print('Started')
time.sleep(10)

print('\n=== TUNNEL STATUS ===')
_, out, _ = ssh.exec_command('systemctl status cloudflared --no-pager 2>&1 | head -15')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== TUNNEL HEALTH CHECK ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/ready 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== MAKING TEST REQUEST FROM VM ===')
_, out, _ = ssh.exec_command('curl -v https://sandbox.mycosoft.com/ 2>&1 | head -30')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK TUNNEL LOGS AFTER REQUEST ===')
time.sleep(2)
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 20 --no-pager 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== TUNNEL METRICS ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/metrics 2>&1 | grep -E "tunnel_total_requests|tunnel_request_errors"')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
