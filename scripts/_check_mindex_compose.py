#!/usr/bin/env python3
"""Check MINDEX docker compose config on VM 189"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.189', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace')

print('[1] Find docker-compose files...')
print(run('find /home/mycosoft -name "docker-compose*.yml" -o -name "compose.yaml" 2>/dev/null | head -10'))

print('\n[2] Check running postgres env...')
print(run('docker inspect mindex-postgres --format "{{range .Config.Env}}{{println .}}{{end}}" 2>/dev/null | grep -i postgres'))

print('\n[3] Check mindex-api env...')
print(run('docker inspect mindex-api --format "{{range .Config.Env}}{{println .}}{{end}}" 2>/dev/null | grep -i mindex'))

print('\n[4] Check network...')
print(run('docker network ls | grep -i mindex'))

ssh.close()
