#!/usr/bin/env python3
"""Fix API environment variables and restart."""
import os
import sys
import time
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

creds_file = Path(__file__).parent.parent / ".credentials.local"
for line in creds_file.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.189', username='mycosoft', password=os.environ['VM_SSH_PASSWORD'], timeout=30)

def run(cmd, timeout=60):
    print(f'\n> {cmd[:80]}...')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').lstrip('\ufeff')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print(f'STDERR: {err}')
    return out, exit_code

# Stop and remove the old container
print("1. Stopping old container...")
run('docker stop mindex-api')
run('docker rm mindex-api')

# Restart with correct environment variables
print("\n2. Starting container with correct DB env vars...")
docker_run_cmd = """
docker run -d --name mindex-api \\
  --network mindex_mindex-network \\
  -p 8000:8000 \\
  -v /home/mycosoft/mindex:/app \\
  -w /app \\
  -e MINDEX_DB_HOST=db \\
  -e MINDEX_DB_PORT=5432 \\
  -e MINDEX_DB_USER=mindex \\
  -e MINDEX_DB_PASSWORD=mindex \\
  -e MINDEX_DB_NAME=mindex \\
  -e REDIS_URL=redis://redis:6379/0 \\
  -e QDRANT_URL=http://qdrant:6333 \\
  --restart unless-stopped \\
  mindex-api:latest \\
  uvicorn mindex_api.main:app --host 0.0.0.0 --port 8000 --reload
"""
run(docker_run_cmd)

# Wait for startup
print("\n3. Waiting 15s for startup...")
time.sleep(15)

# Check container status
print("\n4. Container status:")
run('docker ps | grep mindex-api')

# Verify the DSN is now correct
print("\n5. Verify DSN:")
run('echo "from mindex_api.config import settings; print(settings.mindex_db_dsn)" | docker exec -i mindex-api python')

# Test health
print("\n6. Health check:")
run('curl -s http://localhost:8000/api/mindex/health')

client.close()
print('\nDone.')
