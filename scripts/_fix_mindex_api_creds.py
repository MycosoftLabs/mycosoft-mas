#!/usr/bin/env python3
"""Fix MINDEX API credentials to match postgres on VM 189"""
import paramiko
import time
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.189', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    return stdout.read().decode('utf-8', errors='replace') + stderr.read().decode('utf-8', errors='replace')

print('[1] Stop mindex-api...')
print(run('docker stop mindex-api'))

print('\n[2] Remove mindex-api...')
print(run('docker rm mindex-api'))

print('\n[3] Get the image name...')
images = run('docker images --format "{{.Repository}}:{{.Tag}}" | grep -i mindex-api | head -1')
image = images.strip() or 'mindex-api:latest'
print(f'Using image: {image}')

print('\n[4] Start mindex-api with correct credentials...')
cmd = f'''docker run -d --name mindex-api \\
    --network mindex_mindex-network \\
    -p 8000:8000 \\
    -e MINDEX_DB_HOST=mindex-postgres \\
    -e MINDEX_DB_PORT=5432 \\
    -e MINDEX_DB_USER=mycosoft \\
    -e MINDEX_DB_PASSWORD=REDACTED_DB_PASSWORD \\
    -e MINDEX_DB_NAME=mindex \\
    -e API_CORS_ORIGINS='["http://localhost:3000","http://localhost:3010","http://192.168.0.187:3000","http://192.168.0.172:3010","https://mycosoft.com","https://sandbox.mycosoft.com"]' \\
    --restart unless-stopped \\
    {image}'''
print(run(cmd))

print('\n[5] Wait 10s for API startup...')
time.sleep(10)

print('\n[6] Container status...')
print(run('docker ps --filter name=mindex-api'))

print('\n[7] Health check...')
print(run('curl -s http://localhost:8000/api/mindex/health'))

print('\n[8] Test taxa endpoint...')
result = run('curl -s "http://localhost:8000/api/mindex/taxa?q=amanita&limit=3"')
print(result[:500] if len(result) > 500 else result)

ssh.close()
print('\nDone!')
