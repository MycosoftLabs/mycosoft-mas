#!/usr/bin/env python3
"""Check PostgreSQL configuration."""
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

# Check docker-compose postgres config
print("Checking docker-compose.yml postgres config...")
run('cat /home/mycosoft/mindex/docker-compose.yml | grep -A 20 "db:"')

# Check environment variables in postgres container
print("\nChecking postgres container environment...")
run('docker inspect mindex-postgres --format "{{json .Config.Env}}"')

# Check what user postgres is running as
print("\nChecking postgres process user...")
run('docker exec mindex-postgres id')

# Check if we can connect with the env vars from docker-compose
print("\nChecking what POSTGRES_USER was set to...")
run('docker exec mindex-postgres printenv POSTGRES_USER')
run('docker exec mindex-postgres printenv POSTGRES_PASSWORD')
run('docker exec mindex-postgres printenv POSTGRES_DB')

# Try to list databases using the configured superuser
print("\nListing databases...")
postgres_user = run('docker exec mindex-postgres printenv POSTGRES_USER').strip()
if postgres_user:
    run(f'docker exec mindex-postgres psql -U {postgres_user} -c "SELECT datname FROM pg_database;"')

client.close()
print('\nDone.')
