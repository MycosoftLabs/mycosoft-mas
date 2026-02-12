#!/usr/bin/env python3
"""Pull latest code and redeploy MINDEX API"""
import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.189', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=60)

def run_cmd(cmd, print_output=True, timeout=300):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if print_output and out.strip():
        print(out[-3000:] if len(out) > 3000 else out)
    if err.strip() and 'Warning' not in err:
        print('STDERR:', err[-1000:] if len(err) > 1000 else err)
    return out, err

# Pull latest
print('Pulling latest code...')
run_cmd('cd /home/mycosoft/mindex && git pull')

# Stop old container
print('\nStopping old container...')
run_cmd('docker stop mindex-api; docker rm mindex-api 2>/dev/null; true')
run_cmd("lsof -ti:8000 | xargs -r kill -9 2>/dev/null; true")
time.sleep(2)

# Rebuild without cache
print('\nRebuilding without cache...')
run_cmd('cd /home/mycosoft/mindex && docker build --no-cache -t mindex-api:latest . 2>&1 | tail -25')

# Get network
out, _ = run_cmd('docker network ls --format "{{.Name}}" | grep -i mindex', False)
network_name = out.strip().split('\n')[0] if out.strip() else 'bridge'

# Start with correct credentials
print(f'\nStarting container on network {network_name}...')
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

# Wait and test
time.sleep(8)
print('\nHealth check:')
run_cmd('curl -s http://localhost:8000/api/mindex/health')

print('\nTesting taxa endpoint:')
run_cmd('curl -s "http://localhost:8000/api/mindex/taxa?q=amanita&limit=2" | head -c 500')

c.close()
print('\n\nDone!')
