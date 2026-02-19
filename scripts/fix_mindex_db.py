#!/usr/bin/env python3
"""Fix MINDEX DB connection by using correct hostname."""
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
client.connect('192.168.0.189', username='mycosoft', password=os.environ['VM_SSH_PASSWORD'])

def run(cmd):
    print(f'\n=== {cmd[:70]} ===')
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print(f'STDERR: {err}')
    return out

# Check network aliases for postgres container
run('docker inspect mindex-postgres --format "{{json .NetworkSettings.Networks}}"')

# Check if db service name works
run('docker exec mindex-api curl -s --connect-timeout 2 telnet://db:5432 2>&1 || echo "db:5432 not reachable"')
run('docker exec mindex-api curl -s --connect-timeout 2 telnet://mindex-postgres:5432 2>&1 || echo "mindex-postgres:5432 not reachable"')

# Check current env in container
run('docker exec mindex-api printenv DATABASE_URL')

client.close()
print('\nDone.')
