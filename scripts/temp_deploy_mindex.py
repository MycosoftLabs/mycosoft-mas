#!/usr/bin/env python3
"""Deploy MINDEX API to VM 189 with Settings fix."""
import os
import sys
import time
from pathlib import Path

# Load credentials
creds_file = Path(__file__).parent.parent / ".credentials.local"
if creds_file.exists():
    for line in creds_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: No VM_SSH_PASSWORD found")
    sys.exit(1)

import paramiko

def run_command(client, cmd, timeout=600):
    print(f'\n--- {cmd[:80]} ---')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        print(out.encode('ascii', errors='replace').decode('ascii'))
    if err:
        print(f'STDERR: {err.encode("ascii", errors="replace").decode("ascii")}')
    print(f'Exit code: {exit_code}')
    return exit_code, out, err

def main():
    print('=== MINDEX API Deployment to VM 189 ===')
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print('\n[1/7] Connecting to 192.168.0.189...')
        client.connect('192.168.0.189', username='mycosoft', password=password, timeout=30)
        print('Connected!')
        
        print('\n[2/7] Updating code (git fetch + reset)...')
        run_command(client, 'cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main')
        
        print('\n[3/7] Stopping old container...')
        run_command(client, 'docker rm -f mindex-api 2>/dev/null || true')
        
        print('\n[4/7] Rebuilding Docker image (this may take a while)...')
        code, out, err = run_command(client, 'cd /home/mycosoft/mindex && docker build -t mindex_api --no-cache .', timeout=900)
        if code != 0:
            print('ERROR: Docker build failed!')
            return 1
        
        print('\n[5/7] Starting mindex-api container...')
        run_command(client, '''docker run -d \
          --name mindex-api \
          --network mindex_mindex-network \
          -p 8000:8000 \
          -e DATABASE_URL=postgresql://mindex:mindex@mindex-postgres:5432/mindex \
          -e REDIS_URL=redis://mindex-redis:6379/0 \
          -e QDRANT_URL=http://mindex-qdrant:6333 \
          -v /home/mycosoft/mindex:/app \
          -w /app \
          --restart unless-stopped \
          mindex_api \
          uvicorn mindex_api.main:app --host 0.0.0.0 --port 8000''')
        
        print('\n[6/7] Waiting for container to start...')
        time.sleep(5)
        run_command(client, 'docker ps --filter name=mindex-api --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
        run_command(client, 'docker logs mindex-api --tail 30')
        
        print('\n[7/7] Health check...')
        time.sleep(3)
        code, out, err = run_command(client, 'curl -s http://localhost:8000/api/mindex/health')
        
        if 'healthy' in out.lower() or '"status"' in out.lower():
            print('\n=== SUCCESS: MINDEX API deployed and healthy! ===')
            return 0
        else:
            print('\n=== WARNING: Health check did not return expected response ===')
            return 1
        
    finally:
        client.close()
        print('\nConnection closed.')

if __name__ == '__main__':
    sys.exit(main())
