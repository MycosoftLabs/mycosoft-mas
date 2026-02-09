#!/usr/bin/env python3
"""Rebuild MAS container with Earth-2 integration."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=10)

print('=== Step 1: Check current container ===')
stdin, stdout, stderr = ssh.exec_command('docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep myca', timeout=10)
print(stdout.read().decode())

print('\n=== Step 2: Check Dockerfile location ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /home/mycosoft/mycosoft/mas/Dockerfile* 2>&1', timeout=10)
print(stdout.read().decode())

print('\n=== Step 3: Stop the current container ===')
stdin, stdout, stderr = ssh.exec_command('docker stop myca-orchestrator-new', timeout=30)
print(f'OUT: {stdout.read().decode()}')
print(f'ERR: {stderr.read().decode()}')

print('\n=== Step 4: Build new image ===')
cmd = 'cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache . 2>&1'
print(f'Running: {cmd}')
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=600)  # 10 min timeout for build
output = stdout.read().decode()
print(output[-3000:] if len(output) > 3000 else output)  # Last 3000 chars

print('\n=== Step 5: Remove old container ===')
stdin, stdout, stderr = ssh.exec_command('docker rm myca-orchestrator-new', timeout=30)
print(f'OUT: {stdout.read().decode()}')

print('\n=== Step 6: Start new container ===')
# Optional: mount SSH key for container -> 187 (coding API)
key_on_188 = '/home/mycosoft/.ssh/mas_to_sandbox'
stdin, stdout, stderr = ssh.exec_command(f'test -f {key_on_188} && echo exists', timeout=5)
key_exists = 'exists' in stdout.read().decode()
if key_exists:
    cmd = f'''docker run -d --name myca-orchestrator-new \\
  --restart unless-stopped \\
  -p 8001:8000 \\
  -e REDIS_URL=redis://192.168.0.188:6379/0 \\
  -e DATABASE_URL=postgresql://mycosoft:mycosoft@192.168.0.188:5432/mindex \\
  -e N8N_URL=http://192.168.0.188:5678 \\
  -e MAS_SSH_KEY_PATH=/run/secrets/mas_ssh_key \\
  -v {key_on_188}:/run/secrets/mas_ssh_key:ro \\
  mycosoft/mas-agent:latest'''
else:
    cmd = '''docker run -d --name myca-orchestrator-new \\
  --restart unless-stopped \\
  -p 8001:8000 \\
  -e REDIS_URL=redis://192.168.0.188:6379/0 \\
  -e DATABASE_URL=postgresql://mycosoft:mycosoft@192.168.0.188:5432/mindex \\
  -e N8N_URL=http://192.168.0.188:5678 \\
  mycosoft/mas-agent:latest'''
print(f'Running: {cmd}')
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
print(f'OUT: {stdout.read().decode()}')
print(f'ERR: {stderr.read().decode()}')

print('\n=== Step 7: Wait for startup ===')
time.sleep(10)

print('\n=== Step 8: Verify Earth-2 API ===')
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8001/api/earth2/health', timeout=30)
print(f'Health check: {stdout.read().decode()}')

print('\n=== Step 9: Check container logs ===')
stdin, stdout, stderr = ssh.exec_command('docker logs myca-orchestrator-new --tail 20 2>&1', timeout=30)
print(stdout.read().decode())

ssh.close()
print('\n=== Rebuild complete! ===')
