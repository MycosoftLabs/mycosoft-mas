#!/usr/bin/env python3
"""Test DB connection from inside API container."""
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
    print(f'\n=== CMD ===')
    print(cmd[:200])
    print('===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f'EXIT: {exit_code}')
    print(out)
    if err:
        print(f'STDERR: {err}')
    return exit_code

# Test 1: Try SQLAlchemy connection
print("Test 1: SQLAlchemy database check...")
test_script = '''
import sys
try:
    from mindex_api.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("DB OK:", result.scalar())
except Exception as e:
    print(f"DB ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
'''
run(f'docker exec mindex-api python -c "{test_script}"')

# Test 2: Check health endpoint logic
print("\nTest 2: Check health endpoint code...")
run('docker exec mindex-api cat /app/mindex_api/routers/health.py | head -80')

client.close()
print('\nDone.')
