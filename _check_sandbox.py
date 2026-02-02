#!/usr/bin/env python3
"""Check sandbox status"""
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)

# Check build log
print('=== Build log (last 30 lines) ===')
stdin, stdout, stderr = client.exec_command('tail -30 /tmp/docker-build.log 2>/dev/null || echo "No build log"', timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

# Check container status
print('\n=== Container Status ===')
stdin, stdout, stderr = client.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}'", timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

# Test website
print('\n=== Website Health Check ===')
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:3000/api/health 2>/dev/null | head -5', timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print('\nDone!')
