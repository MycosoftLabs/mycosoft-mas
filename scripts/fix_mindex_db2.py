#!/usr/bin/env python3
"""Fix MINDEX DB connection."""
import os
from pathlib import Path
import paramiko

creds_file = Path(__file__).parent.parent / ".credentials.local"
for line in creds_file.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.189', username='mycosoft', password=os.environ['VM_SSH_PASSWORD'], timeout=30)

def run(cmd, timeout=30):
    print(f'\n=== {cmd[:70]} ===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print(f'STDERR: {err}')
    return out

# Check postgres network aliases
print("Checking postgres container network...")
run('docker inspect mindex-postgres --format "Aliases: {{range .NetworkSettings.Networks}}{{.Aliases}}{{end}}"')

# The docker-compose.yml uses "db" as service name, so inside the network it should be "db"
# But we started the API with mindex-postgres - let me check what names are resolvable

# Quick connectivity test using docker exec with timeout
run('docker exec mindex-api timeout 2 bash -c "echo > /dev/tcp/db/5432 && echo db:5432 OK || echo db:5432 FAIL" 2>&1', timeout=10)
run('docker exec mindex-api timeout 2 bash -c "echo > /dev/tcp/mindex-postgres/5432 && echo mindex-postgres:5432 OK || echo mindex-postgres:5432 FAIL" 2>&1', timeout=10)

# Check current DATABASE_URL
run('docker exec mindex-api printenv DATABASE_URL')

client.close()
print('\nDone.')
