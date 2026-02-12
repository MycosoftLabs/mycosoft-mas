#!/usr/bin/env python3
"""Restart MINDEX API with correct DB credentials"""
import paramiko
import time
import sys

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
    if err.strip() and 'Warning' not in err:
        print('STDERR:', err)
    return out, err

# Stop old container
print('Stopping old container...')
run_cmd('docker stop mindex-api; docker rm mindex-api 2>/dev/null; true')

# Kill any process on 8000
run_cmd("lsof -ti:8000 | xargs -r kill -9 2>/dev/null; true")
time.sleep(2)

# Get network
out, _ = run_cmd('docker network ls --format "{{.Name}}" | grep -i mindex', False)
network_name = out.strip().split('\n')[0] if out.strip() else 'bridge'
print(f'Using network: {network_name}')

# Start with CORRECT credentials
print('\nStarting mindex-api with correct credentials...')
run_cmd(f'''
docker run -d --name mindex-api \\
    --network {network_name} \\
    -p 8000:8000 \\
    -e MINDEX_DB_HOST=mindex-postgres \\
    -e MINDEX_DB_PORT=5432 \\
    -e MINDEX_DB_USER=mycosoft \\
    -e MINDEX_DB_PASSWORD=REDACTED_DB_PASSWORD \\
    -e MINDEX_DB_NAME=mindex \\
    -e API_CORS_ORIGINS='["http://localhost:3000","http://localhost:3010","http://192.168.0.187:3000","http://192.168.0.172:3010"]' \\
    --restart unless-stopped \\
    mindex-api:latest
''')

# Wait for startup
time.sleep(8)

# Check logs
print('\nRecent logs:')
run_cmd('docker logs mindex-api --tail 15 2>&1')

# Test health
print('\nHealth check:')
run_cmd('curl -s http://localhost:8000/api/mindex/health')

# Test taxa
print('\nTesting taxa endpoint:')
run_cmd('curl -s "http://localhost:8000/api/mindex/taxa?q=amanita&limit=2"')

c.close()
print('\nDone!')
