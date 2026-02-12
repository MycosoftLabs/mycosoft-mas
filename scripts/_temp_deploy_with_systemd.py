#!/usr/bin/env python3
"""Stop systemd service and deploy MINDEX API via Docker"""

import paramiko
import time

host = '192.168.0.189'
user = 'mycosoft'
password = 'Mushroom1!Mushroom1!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

print('=== MINDEX API Deployment ===\n')

# Step 1: Stop systemd service
print('Step 1: Stopping systemd mindex-api.service...')
# Use sudo with password via stdin
stdin, stdout, stderr = client.exec_command('echo "Mushroom1!Mushroom1!" | sudo -S systemctl stop mindex-api.service', timeout=30)
stdout.read()
time.sleep(2)

# Disable it so it doesn't restart on boot
stdin, stdout, stderr = client.exec_command('echo "Mushroom1!Mushroom1!" | sudo -S systemctl disable mindex-api.service', timeout=30)
stdout.read()
print('Systemd service stopped and disabled.')

# Step 2: Remove any failed docker containers
print('Step 2: Cleaning up Docker containers...')
stdin, stdout, stderr = client.exec_command('docker rm -f mindex-api 2>/dev/null || true')
stdout.read()
time.sleep(3)

# Step 3: Verify port is free
print('Step 3: Verifying port 8000 is free...')
stdin, stdout, stderr = client.exec_command('sudo ss -tlnp | grep 8000')
port_check = stdout.read().decode('utf-8', errors='replace').strip()
if port_check:
    print(f'Port still in use: {port_check}')
    print('Killing process...')
    stdin, stdout, stderr = client.exec_command('echo "Mushroom1!Mushroom1!" | sudo -S fuser -k 8000/tcp')
    stdout.read()
    time.sleep(3)
else:
    print('Port 8000 is free.')

# Step 4: Get postgres IP
print('Step 4: Getting postgres container IP...')
stdin, stdout, stderr = client.exec_command("docker inspect mindex-postgres --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'")
postgres_ip = stdout.read().decode('utf-8', errors='replace').strip()
print(f'Postgres IP: {postgres_ip}')

# Step 5: Start Docker container
print('Step 5: Starting MINDEX API Docker container...')
cmd = f'''docker run -d --name mindex-api \
    -p 8000:8000 \
    --restart unless-stopped \
    -e MINDEX_DB_HOST={postgres_ip} \
    -e MINDEX_DB_PORT=5432 \
    -e MINDEX_DB_USER=mindex \
    -e MINDEX_DB_PASSWORD=mindex \
    -e MINDEX_DB_NAME=mindex \
    -e API_TITLE="MINDEX API" \
    -e API_VERSION="0.2.0" \
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
out = stdout.read().decode('utf-8', errors='replace').strip()
err = stderr.read().decode('utf-8', errors='replace').strip()

if out and 'Error' not in err:
    print(f'Container started: {out[:12]}')
else:
    print(f'Output: {out}')
    if err:
        print(f'Error: {err}')

# Step 6: Wait for healthy
print('\nStep 6: Waiting for container to become healthy...')
for i in range(20):
    time.sleep(3)
    stdin, stdout, stderr = client.exec_command('docker ps --format "{{.Status}}" --filter name=mindex-api')
    status = stdout.read().decode('utf-8', errors='replace').strip()
    if 'healthy' in status.lower():
        print(f'Container is healthy!')
        break
    elif not status or 'Created' in status:
        stdin, stdout, stderr = client.exec_command('docker logs mindex-api --tail 3 2>&1')
        logs = stdout.read().decode('utf-8', errors='replace').strip()
        print(f'Container status: {status or "not found"}')
        if logs:
            print(f'Logs: {logs}')
        break
    else:
        print(f'  Waiting... ({status})')
else:
    print('Timeout waiting for healthy status')

# Final verification
print('\n=== Final Verification ===')

# Container status
stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mindex')
print('\nContainers:')
print(stdout.read().decode('utf-8', errors='replace'))

# Health check
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/api/mindex/health')
health = stdout.read().decode('utf-8', errors='replace')
print(f'Health: {health}')

client.close()
print('\n=== DEPLOYMENT COMPLETE ===')
