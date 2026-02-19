#!/usr/bin/env python3
"""Check database configuration in API container."""
import os
import sys
from pathlib import Path
import paramiko

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

creds_file = Path(__file__).parent.parent / ".credentials.local"
for line in creds_file.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.189', username='mycosoft', password=os.environ['VM_SSH_PASSWORD'], timeout=30)

def run(cmd, timeout=30):
    print(f'\n=== {cmd[:60]} ===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    # Remove BOM if present
    out = out.lstrip('\ufeff')
    print(out[:3000] if len(out) > 3000 else out)
    return out

print("1. database.py content:")
run('docker exec mindex-api cat /app/mindex_api/database.py')

print("\n2. dependencies.py content:")
run('docker exec mindex-api cat /app/mindex_api/dependencies.py')

print("\n3. Check if asyncpg is installed:")
run('docker exec mindex-api pip list | grep -i asyncpg')

print("\n4. Check requirements for DB drivers:")
run('docker exec mindex-api cat /app/requirements.txt | grep -i -E "(asyncpg|psycopg|sqlalchemy)"')

client.close()
print('\nDone.')
