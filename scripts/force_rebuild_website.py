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

print('=== FORCE REBUILDING WEBSITE FROM SOURCE ===')

print('\n[1] Check current Docker image:')
_, out, _ = ssh.exec_command('docker images | grep website')
print(out.read().decode('utf-8', errors='replace'))

print('\n[2] Check website source Dockerfile:')
_, out, _ = ssh.exec_command('ls -la /opt/mycosoft/website/Dockerfile 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[3] Check docker-compose in website folder:')
_, out, _ = ssh.exec_command('head -30 /opt/mycosoft/website/docker-compose.yml 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[4] Building new image from website source...')
print('    This may take several minutes...')
_, out, err = ssh.exec_command(f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest . 2>&1', timeout=900)
exit_code = out.channel.recv_exit_status()
output = out.read().decode('utf-8', errors='replace')
print(f'Build exit code: {exit_code}')
lines = output.strip().split('\n')
# Print last 30 lines
print('\n'.join(lines[-30:]))

print('\n[5] Restarting container with new image...')
_, out, _ = ssh.exec_command(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')
out.channel.recv_exit_status()
print(out.read().decode('utf-8', errors='replace'))

print('\n[6] Waiting for startup (30 seconds)...')
time.sleep(30)

print('\n[7] Container status:')
_, out, _ = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"')
print(out.read().decode('utf-8', errors='replace'))

print('\n[8] Check new image timestamp:')
_, out, _ = ssh.exec_command('docker images | grep website')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
print('\n=== DONE - Clear Cloudflare cache and test! ===')
