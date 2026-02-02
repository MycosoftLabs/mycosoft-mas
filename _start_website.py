#!/usr/bin/env python3
"""Start website container directly"""
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)

# Run website container directly
print('=== Starting website container directly ===')
cmd = """docker run -d --name mycosoft-website \
  --restart unless-stopped \
  -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets \
  -e NODE_ENV=production \
  --network mycosoft-production_mycosoft-network \
  website-website:latest"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

print('\n=== Container Status ===')
stdin, stdout, stderr = client.exec_command("docker ps --filter 'name=mycosoft-website' --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'", timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

print('\n=== Testing website ===')
stdin, stdout, stderr = client.exec_command('sleep 5 && curl -s http://localhost:3000/ | head -20', timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print('\nDone!')
