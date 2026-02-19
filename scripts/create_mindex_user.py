#!/usr/bin/env python3
"""Create mindex user for MINDEX API."""
import os
from pathlib import Path
import paramiko
import time

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
    return out, exit_code

# Connect using the actual superuser (mycosoft) and mindex database
print("Checking existing users with mycosoft superuser...")
run('docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT usename FROM pg_user;"')

# Create mindex user
print("\nCreating mindex user...")
run('docker exec mindex-postgres psql -U mycosoft -d mindex -c "CREATE USER mindex WITH PASSWORD \'mindex\' CREATEDB;"')

# Grant all privileges on mindex database to mindex user
print("\nGranting privileges...")
run('docker exec mindex-postgres psql -U mycosoft -d mindex -c "GRANT ALL PRIVILEGES ON DATABASE mindex TO mindex;"')
run('docker exec mindex-postgres psql -U mycosoft -d mindex -c "GRANT ALL PRIVILEGES ON SCHEMA public TO mindex;"')
run('docker exec mindex-postgres psql -U mycosoft -d mindex -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mindex;"')
run('docker exec mindex-postgres psql -U mycosoft -d mindex -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mindex;"')

# Verify mindex user can connect
print("\nVerifying mindex user can connect...")
out, exit_code = run('docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT 1 as test;"')

if exit_code == 0:
    print("\n✓ mindex user can connect!")
    
    # Restart API
    print("\nRestarting mindex-api...")
    run('docker restart mindex-api')
    
    print("\nWaiting 10s for API to restart...")
    time.sleep(10)
    
    # Test health
    print("\nTesting API health...")
    run('curl -s http://localhost:8000/api/mindex/health')
else:
    print("\n✗ mindex user connection failed!")

client.close()
print('\nDone.')
