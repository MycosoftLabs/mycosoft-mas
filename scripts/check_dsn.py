#!/usr/bin/env python3
"""Check mindex_db_dsn configuration."""
import os
import sys
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

def run(cmd, timeout=30):
    print(f'\n> {cmd[:70]}...')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').lstrip('\ufeff')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print(f'STDERR: {err}')
    return out, exit_code

# Create a small test script inside the container
test_script = """
from mindex_api.config import settings
print("mindex_db_dsn:", settings.mindex_db_dsn)
print("DATABASE_URL env:", __import__('os').environ.get('DATABASE_URL', 'NOT SET'))
"""

# Write and execute the test script
run('echo -e "from mindex_api.config import settings\\nprint(settings.mindex_db_dsn)" | docker exec -i mindex-api python')

# Check grep for mindex_db_dsn in config.py
print("\nConfig file definition of mindex_db_dsn:")
run('docker exec mindex-api grep -n -B2 -A10 "mindex_db_dsn" /app/mindex_api/config.py | head -40')

client.close()
print('\nDone.')
