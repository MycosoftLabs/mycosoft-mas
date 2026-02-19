#!/usr/bin/env python3
"""Final status check."""
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

print("Container status:")
stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mindex-api', timeout=30)
stdout.channel.recv_exit_status()
print(stdout.read().decode('utf-8', errors='replace'))

print("\nFinal health check:")
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/api/mindex/health', timeout=30)
stdout.channel.recv_exit_status()
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
