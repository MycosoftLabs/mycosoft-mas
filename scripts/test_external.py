import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== TEST EXTERNAL ACCESS FROM VM ===')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" https://sandbox.mycosoft.com/ 2>&1')
print(f'External request result: {out.read().decode("utf-8", errors="replace")}')

print('\n=== GET THE TUNNEL STATUS FROM CLOUDFLARE ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/metrics 2>&1 | grep "tunnel_" | head -20')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK TUNNEL HEALTH ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/ready 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== NOW CHECK LIVE LOGS ===')
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 15 --no-pager 2>&1 | tail -15')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
