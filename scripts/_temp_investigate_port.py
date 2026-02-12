#!/usr/bin/env python3
"""Investigate what's holding port 8000"""

import paramiko

host = '192.168.0.189'
user = 'mycosoft'
password = 'Mushroom1!Mushroom1!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

print('=== Investigating port 8000 ===\n')

# Check what's listening on 8000
print('1. ss -tlnp output:')
stdin, stdout, stderr = client.exec_command('sudo ss -tlnp | grep 8000')
print(stdout.read().decode('utf-8', errors='replace'))

# Check netstat 
print('2. netstat output:')
stdin, stdout, stderr = client.exec_command('sudo netstat -tlnp | grep 8000')
print(stdout.read().decode('utf-8', errors='replace'))

# Check lsof
print('3. lsof output:')
stdin, stdout, stderr = client.exec_command('sudo lsof -i :8000')
print(stdout.read().decode('utf-8', errors='replace'))

# Check all docker containers
print('4. All docker containers:')
stdin, stdout, stderr = client.exec_command('docker ps -a')
print(stdout.read().decode('utf-8', errors='replace'))

# Check docker networks
print('5. Docker networks:')
stdin, stdout, stderr = client.exec_command('docker network ls')
print(stdout.read().decode('utf-8', errors='replace'))

# Check for any process with uvicorn
print('6. Uvicorn processes:')
stdin, stdout, stderr = client.exec_command('ps aux | grep uvicorn')
print(stdout.read().decode('utf-8', errors='replace'))

# Check systemd services
print('7. Systemd mindex services:')
stdin, stdout, stderr = client.exec_command('systemctl list-units | grep -i mindex')
print(stdout.read().decode('utf-8', errors='replace') or '(none found)')

client.close()
