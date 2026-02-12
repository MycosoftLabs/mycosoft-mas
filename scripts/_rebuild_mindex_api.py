#!/usr/bin/env python3
"""Rebuild and restart MINDEX API container"""
import paramiko
import time
import sys

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.189', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)

def run_cmd(cmd, print_output=True):
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if print_output and out.strip():
        print(out)
    if err.strip():
        print('STDERR:', err)
    return out, err

print('Rebuilding MINDEX API...')
run_cmd('cd /home/mycosoft/mindex && docker build -t mindex-api:latest . 2>&1 | tail -20')

print('Stopping old container...')
run_cmd('docker stop mindex-api; docker rm mindex-api 2>/dev/null; true')

print('Starting new container...')
run_cmd('''
cd /home/mycosoft/mindex && docker run -d --name mindex-api \
    --network mindex_default \
    -p 8000:8000 \
    -e MINDEX_DB_HOST=mindex-postgres \
    -e MINDEX_DB_PORT=5432 \
    -e MINDEX_DB_USER=mindex \
    -e MINDEX_DB_PASSWORD=mindex_secure_password \
    -e MINDEX_DB_NAME=mindex \
    -e API_CORS_ORIGINS='["http://localhost:3000","http://localhost:3010","http://192.168.0.187:3000","http://192.168.0.172:3010"]' \
    --restart unless-stopped \
    mindex-api:latest
''')

# Wait and check status
time.sleep(5)
out, _ = run_cmd('docker ps --filter name=mindex-api --format "{{.Names}} {{.Status}}"')
print('STATUS:', out)

c.close()
print('Done!')
