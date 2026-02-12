#!/usr/bin/env python3
"""Full MINDEX API restart - kill port, clean up, restart"""
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

# Check what's using port 8000
print('Checking port 8000...')
run_cmd('ss -tlnp | grep 8000 || echo "Port 8000 is free"')

# Stop all mindex-api containers/processes
print('\nStopping any mindex-api containers...')
run_cmd('docker stop mindex-api 2>/dev/null; docker rm mindex-api 2>/dev/null; true')

# Kill any uvicorn on 8000
print('\nKilling processes on port 8000...')
run_cmd("lsof -ti:8000 | xargs -r kill -9 2>/dev/null; true")

# Wait for port to free
time.sleep(2)

# Verify port is free
print('\nVerifying port 8000 is free...')
run_cmd('ss -tlnp | grep 8000 || echo "Port 8000 is now free"')

# Get network name
print('\nGetting network...')
out, _ = run_cmd('docker network ls --format "{{.Name}}" | grep -i mindex', False)
network_name = out.strip().split('\n')[0] if out.strip() else 'bridge'
print(f'Using network: {network_name}')

# Start container
print('\nStarting mindex-api container...')
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
print('\nWaiting for container to start...')
time.sleep(8)

# Check status
print('\nContainer status:')
run_cmd('docker ps --filter name=mindex-api')

# Check logs
print('\nRecent logs:')
run_cmd('docker logs mindex-api --tail 10')

# Test health
print('\nHealth check:')
run_cmd('curl -s http://localhost:8000/api/mindex/health')

c.close()
print('\nDone!')
