#!/usr/bin/env python3
"""Deploy website after Docker restart - Feb 6, 2026"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=10)

# Pull latest and start website
cmd = '''cd /home/mycosoft/mycosoft/mas && \
git fetch origin && \
git reset --hard origin/main && \
docker compose -f docker-compose.always-on.yml up -d mycosoft-website'''

stdin, stdout, stderr = ssh.exec_command(f'nohup bash -c "{cmd}" > /tmp/startup.log 2>&1 &', timeout=5)
print('Startup triggered - waiting 60s...')

ssh.close()
time.sleep(60)

# Test
import requests
try:
    r = requests.get('https://sandbox.mycosoft.com/api/mycobrain/health', timeout=20)
    print(f'Sandbox status: {r.status_code}')
    if r.status_code == 200:
        print(f'Response: {r.json()}')
except Exception as e:
    print(f'Error: {e}')
