#!/usr/bin/env python3
"""Restart sandbox container with new image"""
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)

print('=== Stopping old container ===')
stdin, stdout, stderr = client.exec_command('docker stop mycosoft-website', timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

print('\n=== Removing old container ===')
stdin, stdout, stderr = client.exec_command('docker rm mycosoft-website', timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

print('\n=== Starting new container ===')
stdin, stdout, stderr = client.exec_command('cd /opt/mycosoft && docker compose up -d mycosoft-website', timeout=60)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

print('\n=== Container Status ===')
stdin, stdout, stderr = client.exec_command("docker ps --filter 'name=mycosoft-website' --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'", timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print('\nDone!')
