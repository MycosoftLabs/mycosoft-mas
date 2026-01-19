#!/usr/bin/env python3
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

commands = [
    'find /home -name "docker-compose.yml" 2>/dev/null | head -5',
    'find /opt -name "docker-compose.yml" 2>/dev/null | head -5',
    'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"',
    'pwd',
    'ls -la ~/',
]

for cmd in commands:
    print(f'\n>>> {cmd}')
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode().strip())

client.close()
