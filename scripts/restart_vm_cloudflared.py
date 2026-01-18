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

print('=== RESTARTING CLOUDFLARED ON VM ===')

print('\n[1] Restarting cloudflared service...')
_, out, _ = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl restart cloudflared')
out.channel.recv_exit_status()

time.sleep(5)

print('\n[2] Checking status:')
_, out, _ = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S systemctl status cloudflared --no-pager')
print(out.read().decode('utf-8', errors='replace')[:1000])

print('\n[3] Testing localhost:3000:')
_, out, _ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000')
print(f'HTTP Status: {out.read().decode().strip()}')

print('\n[4] Latest tunnel logs:')
_, out, _ = ssh.exec_command(f'echo "{VM_PASS}" | sudo -S journalctl -u cloudflared -n 5 --no-pager')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
print('\n=== DONE - Try https://sandbox.mycosoft.com now ===')
