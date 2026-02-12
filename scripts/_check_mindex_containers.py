#!/usr/bin/env python3
"""Quick script to check MINDEX VM containers"""
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.189', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=15)

# Check running containers
stdin, stdout, stderr = c.exec_command('docker ps --format "{{.Names}} {{.Status}}"')
print('CONTAINERS:')
print(stdout.read().decode())
print(stderr.read().decode())

c.close()
