#!/usr/bin/env python3
"""Debug MINDEX DB connection issue."""
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

# Check full API logs for DB errors
print("Checking API logs for DB errors...")
run('docker logs mindex-api 2>&1 | grep -i -E "(error|exception|database|postgres|connect)" | tail -20')

# Try direct psql connection from API container
print("\nTesting direct psql connection...")
run('docker exec mindex-api python -c "import psycopg2; conn = psycopg2.connect(\\"postgresql://mindex:mindex@mindex-postgres:5432/mindex\\"); print(\\"DB connected!\\"); conn.close()" 2>&1', timeout=15)

# Check postgres logs
print("\nChecking postgres logs...")
run('docker logs mindex-postgres 2>&1 | tail -15')

# Check if mindex database exists
print("\nChecking if mindex database exists...")
run('docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT 1 as test;" 2>&1')

client.close()
print('\nDone.')
