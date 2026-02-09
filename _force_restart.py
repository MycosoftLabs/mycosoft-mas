#!/usr/bin/env python3
"""Force restart website container - Feb 6, 2026"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=10)

# Force remove and recreate in background
cmd = '''
cd /home/mycosoft/mycosoft/mas
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true
docker compose -f docker-compose.always-on.yml up -d mycosoft-website
'''

stdin, stdout, stderr = ssh.exec_command(f'''nohup bash -c '{cmd}' > /tmp/restart.log 2>&1 &
echo "Restart triggered"
''', timeout=5)
print(stdout.read().decode())

ssh.close()
print("Waiting 30 seconds for container to restart...")
time.sleep(30)

# Now test
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=10)

stdin, stdout, stderr = ssh2.exec_command('curl -s http://localhost:3000/api/mycobrain/health', timeout=15)
stdout.channel.settimeout(15)
try:
    result = stdout.read().decode()
    print(f"Website health: {result}")
except:
    print("Timeout reading result - container might still be starting")

ssh2.close()
