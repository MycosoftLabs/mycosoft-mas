#!/usr/bin/env python3
"""Check and fix the unhealthy orchestrator."""

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Connecting to MAS VM (192.168.0.188)...")
client.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=10)
print("Connected!")

# Check orchestrator logs
print("\n" + "=" * 60)
print("Checking myca-orchestrator logs...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('docker logs myca-orchestrator --tail 30 2>&1')
logs = stdout.read().decode().strip()
print(logs[:2000] if logs else "No logs")

# Restart orchestrator if unhealthy
print("\n" + "=" * 60)
print("Restarting myca-orchestrator...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('docker restart myca-orchestrator')
result = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(result if result else err if err else "Restarted")

# Wait and check status
import time
time.sleep(5)

print("\n" + "=" * 60)
print("Checking orchestrator status after restart...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('docker ps --filter name=myca-orchestrator --format "{{.Names}}: {{.Status}}"')
status = stdout.read().decode().strip()
print(status)

client.close()
