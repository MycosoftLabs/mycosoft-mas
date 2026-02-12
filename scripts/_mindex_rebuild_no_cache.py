#!/usr/bin/env python3
"""Rebuild MINDEX without cache and restart"""
import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.189', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=60)

def run_cmd(cmd, print_output=True, timeout=120):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if print_output and out.strip():
        print(out[-3000:] if len(out) > 3000 else out)  # Limit output
    if err.strip() and 'Warning' not in err:
        print('STDERR:', err[-1000:] if len(err) > 1000 else err)
    return out, err

# Check DB connectivity from host
print('Testing DB connection from host...')
run_cmd('docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT 1" 2>&1 | head -5')

# Check if postgres is on the same network
print('\nChecking postgres network...')
run_cmd('docker inspect mindex-postgres --format "{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}" | head -1')

# Rebuild image without cache
print('\nRebuilding mindex-api WITHOUT cache (this takes a minute)...')
out, err = run_cmd('cd /home/mycosoft/mindex && docker build --no-cache -t mindex-api:latest . 2>&1 | tail -30', timeout=300)

# Stop and remove old
print('\nStopping old container...')
run_cmd('docker stop mindex-api; docker rm mindex-api 2>/dev/null; true')

# Kill any leftover process
run_cmd("lsof -ti:8000 | xargs -r kill -9 2>/dev/null; true")
time.sleep(2)

# Get network
out, _ = run_cmd('docker network ls --format "{{.Name}}" | grep -i mindex', False)
network_name = out.strip().split('\n')[0] if out.strip() else 'bridge'
print(f'Using network: {network_name}')

# Start new container
print('\nStarting new container...')
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

# Wait for startup
time.sleep(8)

# Check logs
print('\nRecent logs:')
run_cmd('docker logs mindex-api --tail 15 2>&1')

# Test taxa
print('\nTesting taxa endpoint...')
run_cmd('curl -s "http://localhost:8000/api/mindex/taxa?q=amanita&limit=2"')

c.close()
print('\nDone!')
