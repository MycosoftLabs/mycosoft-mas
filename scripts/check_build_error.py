#!/usr/bin/env python3
"""Check webpack build error details."""
import paramiko
import sys
import os

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['PYTHONIOENCODING'] = 'utf-8'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

# Get build logs with webpack errors
stdin, stdout, stderr = client.exec_command(
    'cd /opt/mycosoft/website && docker compose build website --no-cache 2>&1 | grep -A 50 "error\\|Error\\|failed" | head -80',
    timeout=300
)
output = stdout.read().decode('utf-8', errors='replace')
# Filter to ASCII for Windows console
output = ''.join(c if ord(c) < 128 else '?' for c in output)
print(output)
client.close()
