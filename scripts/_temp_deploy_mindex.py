#!/usr/bin/env python3
"""Temporary script to deploy MINDEX API to VM 192.168.0.189"""

import paramiko
import time

host = '192.168.0.189'
user = 'mycosoft'
password = 'Mushroom1!Mushroom1!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

# Start the API
print('Starting API service...')
stdin, stdout, stderr = client.exec_command('cd /home/mycosoft/mindex && docker-compose up -d api', timeout=120)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

# Wait for container to start
print('Waiting 15 seconds for container to start...')
time.sleep(15)

# Check container status
print('\n=== Container Status ===')
stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mindex')
print(stdout.read().decode('utf-8', errors='replace'))

# Health check
print('\n=== Health Check ===')
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/api/mindex/health')
print(stdout.read().decode('utf-8', errors='replace'))

# Check logs
print('\n=== Recent Logs ===')
stdin, stdout, stderr = client.exec_command('docker logs mindex-api --tail 5 2>&1')
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print('\nDeployment complete!')
