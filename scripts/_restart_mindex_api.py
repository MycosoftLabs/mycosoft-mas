#!/usr/bin/env python3
"""Restart MINDEX API container with latest code"""
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.189', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)

# Restart the API container
print('Restarting mindex-api container...')
stdin, stdout, stderr = c.exec_command('docker restart mindex-api')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err)

# Wait and check health
import time
time.sleep(5)
stdin, stdout, stderr = c.exec_command('docker ps --filter name=mindex-api --format "{{.Names}} {{.Status}}"')
print('STATUS:', stdout.read().decode())

c.close()
print('Done!')
