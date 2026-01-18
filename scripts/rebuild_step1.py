import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== CHECKING CURRENT STATE ===')

print('\n[1] Docker images:')
_, out, _ = ssh.exec_command('docker images --format "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | grep website')
print(out.read().decode('utf-8', errors='replace'))

print('\n[2] Website Dockerfile exists:')
_, out, _ = ssh.exec_command('ls -la /opt/mycosoft/website/Dockerfile')
print(out.read().decode('utf-8', errors='replace'))

print('\n[3] Building image (this will take a few minutes)...')
print('    Starting build...')

ssh.close()
print('\nRun the docker build manually on the VM or wait for next script')
