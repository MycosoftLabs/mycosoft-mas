#!/usr/bin/env python3
"""Rebuild MINDEX API container directly (not via docker-compose)"""

import paramiko
import time

host = '192.168.0.189'
user = 'mycosoft'
password = 'Mushroom1!Mushroom1!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

commands = [
    # Stop and remove the current API container
    ('Stop mindex-api', 'docker stop mindex-api'),
    ('Remove mindex-api', 'docker rm mindex-api'),
    # Build the new image
    ('Build new image', 'cd /home/mycosoft/mindex && docker build -t mindex-api:latest --no-cache .'),
    # Start the new container with the same settings as docker-compose would
    ('Start new container', '''docker run -d --name mindex-api \
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
        uvicorn mindex_api.main:app --host 0.0.0.0 --port 8000 --reload'''),
]

for name, cmd in commands:
    print(f'>>> {name}')
    print(f'    {cmd[:80]}...' if len(cmd) > 80 else f'    {cmd}')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=600)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        print(out[-500:] if len(out) > 500 else out)
    if err:
        print(err[-500:] if len(err) > 500 else err)
    print()

# Wait for container to start
print('Waiting 20 seconds for container to start...')
time.sleep(20)

# Check container status
print('=== Container Status ===')
stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mindex')
print(stdout.read().decode('utf-8', errors='replace'))

# Health check
print('=== Health Check ===')
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/api/mindex/health')
result = stdout.read().decode('utf-8', errors='replace')
print(result if result else '(no response)')

# Check logs
print('\n=== Recent Logs ===')
stdin, stdout, stderr = client.exec_command('docker logs mindex-api --tail 10 2>&1')
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print('\nDeployment complete!')
