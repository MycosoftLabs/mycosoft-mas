#!/usr/bin/env python3
"""Restart MINDEX postgres and API on VM 189"""
import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.189', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace') + stderr.read().decode('utf-8', errors='replace')

print('[1] Check containers...')
print(run('docker ps --format "{{.Names}} {{.Status}}"'))

print('\n[2] Restart mindex-postgres...')
print(run('docker restart mindex-postgres'))

print('\n[3] Wait 10s for postgres...')
time.sleep(10)

print('\n[4] Check postgres status...')
print(run('docker ps --format "{{.Names}} {{.Status}}" | grep postgres'))

print('\n[5] Restart mindex-api...')
print(run('docker restart mindex-api'))

print('\n[6] Wait 8s for API...')
time.sleep(8)

print('\n[7] Health check...')
print(run('curl -s http://localhost:8000/api/mindex/health'))

print('\n[8] Test taxa endpoint...')
print(run('curl -s "http://localhost:8000/api/mindex/taxa?q=amanita&limit=3"'))

ssh.close()
print('\nDone!')
