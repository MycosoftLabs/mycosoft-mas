#!/usr/bin/env python3
"""Kill rogue uvicorn and restart MINDEX API container"""

import paramiko
import time

host = '192.168.0.189'
user = 'mycosoft'
password = 'REDACTED_VM_SSH_PASSWORD'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

# Kill the rogue uvicorn process
print('=== Killing rogue uvicorn process ===')
stdin, stdout, stderr = client.exec_command('sudo kill -9 435482')
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

# Also kill any uvicorn on port 8000
stdin, stdout, stderr = client.exec_command("sudo fuser -k 8000/tcp 2>/dev/null || true")
print(stdout.read().decode('utf-8', errors='replace'))

# Wait a moment
time.sleep(3)

# Remove any existing mindex-api container
print('\n=== Cleaning up containers ===')
stdin, stdout, stderr = client.exec_command('docker rm -f mindex-api 2>/dev/null || true')
print(stdout.read().decode('utf-8', errors='replace'))

# Verify port is free
print('\n=== Verifying port 8000 is free ===')
stdin, stdout, stderr = client.exec_command('sudo ss -tlnp | grep 8000')
out = stdout.read().decode('utf-8', errors='replace')
print(out if out else 'Port 8000 is free!')

# Start the new container
print('\n=== Starting new container ===')
cmd = '''docker run -d --name mindex-api \
    -p 8000:8000 \
    --restart unless-stopped \
    -e MINDEX_DB_HOST=172.17.0.1 \
    -e MINDEX_DB_PORT=5432 \
    -e MINDEX_DB_USER=mindex \
    -e MINDEX_DB_PASSWORD=mindex \
    -e MINDEX_DB_NAME=mindex \
    -e API_TITLE="MINDEX API" \
    -e API_VERSION="0.1.0" \
    -e API_PREFIX="/api/mindex" \
    -v /home/mycosoft/mindex/mindex_api:/app/mindex_api:ro \
    -v /home/mycosoft/mindex/mindex_etl:/app/mindex_etl:ro \
    --health-cmd="curl -f http://localhost:8000/api/mindex/health" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    --health-start-period=40s \
    mindex-api:latest \
    uvicorn mindex_api.main:app --host 0.0.0.0 --port 8000 --reload'''
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print(f'Container ID: {out.strip()[:12]}...' if out else '')
if 'Error' in err:
    print(f'Error: {err}')

# Wait for container to start
print('\nWaiting 15 seconds for container to start...')
time.sleep(15)

# Check container status
print('\n=== Container Status ===')
stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mindex')
print(stdout.read().decode('utf-8', errors='replace'))

# Health check
print('=== Health Check ===')
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/api/mindex/health')
result = stdout.read().decode('utf-8', errors='replace')
print(result if result else '(no response - container may still be starting)')

# Check logs
print('\n=== Recent Logs ===')
stdin, stdout, stderr = client.exec_command('docker logs mindex-api --tail 10 2>&1')
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print('\n=== DEPLOYMENT COMPLETE ===')
