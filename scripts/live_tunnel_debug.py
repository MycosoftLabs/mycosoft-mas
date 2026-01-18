import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== LATEST TUNNEL LOGS (last 20) ===')
_, out, _ = ssh.exec_command('journalctl -u cloudflared -n 20 --no-pager 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK IF CLOUDFLARED CAN REACH LOCALHOST:3000 ===')
# Test with curl from the same user context as cloudflared (root)
_, out, _ = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S curl -s -o /dev/null -w "%{{http_code}}" http://localhost:3000/ 2>&1')
print(f'Result: {out.read().decode("utf-8", errors="replace")}')

print('\n=== CHECK FIREWALL ===')
_, out, _ = ssh.exec_command('echo "Mushroom1!Mushroom1!" | sudo -S iptables -L -n 2>&1 | head -20')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK IF ANY PROCESS IS BLOCKING ===')
_, out, _ = ssh.exec_command('ss -tlnp | grep 3000')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CLOUDFLARED PROCESS ===')
_, out, _ = ssh.exec_command('ps aux | grep cloudflared')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
