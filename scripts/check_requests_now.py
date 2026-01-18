import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== TUNNEL METRICS NOW ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/metrics 2>&1 | grep -E "tunnel_total_requests|tunnel_request_errors|tunnel_concurrent"')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== LAST 10 TUNNEL LOGS ===')
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 10 --no-pager 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK IF ANOTHER TUNNEL IS RUNNING ===')
_, out, _ = ssh.exec_command('ps aux | grep -i cloudflare | grep -v grep')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK FOR ANY OTHER TUNNELS ===')
_, out, _ = ssh.exec_command('docker ps | grep -i cloudflare')
result = out.read().decode('utf-8', errors='replace')
print(result if result else 'No cloudflare containers')

ssh.close()
