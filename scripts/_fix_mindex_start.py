#!/usr/bin/env python3
"""Fix MINDEX API container startup"""
import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.189', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)

def run_cmd(cmd, print_output=True):
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if print_output and out.strip():
        print(out)
    if err.strip():
        print('STDERR:', err)
    return out, err

# Find the correct network
print('Finding Docker networks...')
run_cmd('docker network ls')

# Get postgres container's network
print('\nGetting postgres container network...')
out, _ = run_cmd('docker inspect mindex-postgres --format "{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}"', False)
print('Postgres network:', out.strip()[:12] if out.strip() else 'NOT FOUND')

# Find network by name
out, _ = run_cmd('docker network ls --format "{{.Name}}" | grep -i mindex', False)
network_name = out.strip().split('\n')[0] if out.strip() else None
print('Found network:', network_name)

if not network_name:
    print('Creating mindex network...')
    run_cmd('docker network create mindex_network')
    network_name = 'mindex_network'

# Remove failed container
print('\nCleaning up...')
run_cmd('docker rm -f mindex-api 2>/dev/null; true')

# Start with correct network
print(f'\nStarting mindex-api on network: {network_name}')
run_cmd(f'''
docker run -d --name mindex-api \\
    --network {network_name} \\
    -p 8000:8000 \\
    -e MINDEX_DB_HOST=mindex-postgres \\
    -e MINDEX_DB_PORT=5432 \\
    -e MINDEX_DB_USER=mindex \\
    -e MINDEX_DB_PASSWORD=mindex_secure_password \\
    -e MINDEX_DB_NAME=mindex \\
    -e API_CORS_ORIGINS='["http://localhost:3000","http://localhost:3010","http://192.168.0.187:3000","http://192.168.0.172:3010"]' \\
    --restart unless-stopped \\
    mindex-api:latest
''')

# Wait and check status
time.sleep(5)
print('\nContainer status:')
run_cmd('docker ps --filter name=mindex-api')

# Test health
print('\nHealth check:')
run_cmd('curl -s http://localhost:8000/api/mindex/health')

c.close()
print('\nDone!')
