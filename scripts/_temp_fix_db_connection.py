#!/usr/bin/env python3
"""Fix MINDEX API database connection"""

import paramiko
import time

host = '192.168.0.189'
user = 'mycosoft'
password = 'REDACTED_VM_SSH_PASSWORD'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

# Get the postgres container's IP
print('=== Getting postgres container IP ===')
stdin, stdout, stderr = client.exec_command("docker inspect mindex-postgres --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'")
postgres_ip = stdout.read().decode('utf-8', errors='replace').strip()
print(f'Postgres IP: {postgres_ip}')

# If no IP (not on docker network), use host network
if not postgres_ip:
    postgres_ip = '172.17.0.1'
    print(f'Using Docker host IP: {postgres_ip}')

# Remove existing container
print('\n=== Restarting with correct DB host ===')
stdin, stdout, stderr = client.exec_command('docker rm -f mindex-api 2>/dev/null || true')
print(stdout.read().decode('utf-8', errors='replace'))

time.sleep(2)

# Start with correct postgres IP
cmd = f'''docker run -d --name mindex-api \
    -p 8000:8000 \
    --restart unless-stopped \
    -e MINDEX_DB_HOST={postgres_ip} \
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
print(f'Container ID: {out.strip()[:12]}' if out else '')
if 'Error' in err:
    print(f'Error: {err}')

# Wait for container
print('\nWaiting 15 seconds for container to start...')
time.sleep(15)

# Check health
print('\n=== Health Check ===')
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/api/mindex/health')
result = stdout.read().decode('utf-8', errors='replace')
print(result)

# Check container status
print('\n=== Container Status ===')
stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}" | grep mindex')
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print('\n=== DEPLOYMENT COMPLETE ===')
