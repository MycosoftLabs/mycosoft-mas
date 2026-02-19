#!/usr/bin/env python3
"""Check MINDEX status on VM 189."""
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

cmds = [
    'docker ps --filter name=mindex --format "table {{.Names}}\t{{.Status}}"',
    'docker logs mindex-api --tail 30 2>&1',
    'curl -s http://localhost:8000/api/mindex/health'
]

for cmd in cmds:
    print(f'\n=== {cmd[:60]} ===')
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print(f'STDERR: {err}')

client.close()
print('\nDone.')
