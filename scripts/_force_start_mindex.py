#!/usr/bin/env python3
"""Force start MINDEX API - kill everything and start fresh"""
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
    if print_output:
        if out.strip():
            print(out)
        if err.strip() and 'No such' not in err and 'Warning' not in err:
            print('STDERR:', err)
    return out, err

# Force kill everything on port 8000
print('Force killing port 8000...')
run_cmd('sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true')

# Stop and remove all mindex-api containers
print('\nForce removing all mindex-api containers...')
run_cmd('docker rm -f mindex-api 2>/dev/null || true')
run_cmd('docker rm -f $(docker ps -aq --filter name=mindex-api) 2>/dev/null || true')

# Wait for port to clear
time.sleep(3)

# Verify port is free
print('\nVerifying port 8000...')
out, _ = run_cmd('ss -tlnp | grep 8000 || echo "Port 8000 is FREE"')

# Get network
out, _ = run_cmd('docker network ls --format "{{.Name}}" | grep -i mindex', False)
network_name = out.strip().split('\n')[0] if out.strip() else 'bridge'

# Start container
print(f'\nStarting container on {network_name}...')
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

# Wait
time.sleep(8)

# Check container
print('\nContainer status:')
run_cmd('docker ps --filter name=mindex-api')

# Test
print('\nHealth check:')
run_cmd('curl -s http://localhost:8000/api/mindex/health')

print('\nTaxa test:')
run_cmd('curl -s "http://localhost:8000/api/mindex/taxa?q=amanita&limit=1" | head -c 500')

c.close()
print('\nDone!')
