#!/usr/bin/env python3
"""Fix MINDEX DB user."""
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

# Check existing users
print("Checking existing PostgreSQL users...")
run('docker exec mindex-postgres psql -U postgres -c "SELECT usename FROM pg_user;"')

# Check existing databases
print("\nChecking existing databases...")
run('docker exec mindex-postgres psql -U postgres -c "SELECT datname FROM pg_database;"')

# Create mindex user if it doesn't exist
print("\nCreating mindex user...")
run('docker exec mindex-postgres psql -U postgres -c "CREATE USER mindex WITH PASSWORD \'mindex\' CREATEDB;"')

# Create mindex database if it doesn't exist
print("\nCreating mindex database...")
run('docker exec mindex-postgres psql -U postgres -c "CREATE DATABASE mindex OWNER mindex;"')

# Grant all privileges
print("\nGranting privileges...")
run('docker exec mindex-postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE mindex TO mindex;"')

# Verify connection works
print("\nVerifying mindex user can connect...")
run('docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT 1 as test;"')

# Restart API to pick up the fix
print("\nRestarting mindex-api container...")
run('docker restart mindex-api')

# Wait a bit and test health
import time
print("\nWaiting 10s for API to restart...")
time.sleep(10)

# Test health
print("\nTesting API health...")
run('curl -s http://localhost:8000/api/mindex/health')

client.close()
print('\nDone.')
