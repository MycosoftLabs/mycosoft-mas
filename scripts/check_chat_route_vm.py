import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CHECKING CHAT ROUTE ON VM ===')
_, out, _ = ssh.exec_command('cat /opt/mycosoft/website/app/api/chat/route.ts')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
