#!/usr/bin/env python3
"""Quick check of website container status"""
import paramiko
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print("=" * 60)
print("CHECKING WEBSITE CONTAINER STATUS")
print("=" * 60)

# Check container status
print("\n[1] Container Status:")
stdin, stdout, stderr = ssh.exec_command('docker ps --filter name=mycosoft-website --format "{{.Names}}\t{{.Status}}"')
output = stdout.read().decode('utf-8', errors='replace').replace('\u25b2', '^').replace('\u25bc', 'v')
print(output)

# Check container logs (last 30 lines)
print("\n[2] Recent Logs (last 30 lines):")
stdin, stdout, stderr = ssh.exec_command('docker logs mycosoft-website --tail 30 2>&1')
output = stdout.read().decode('utf-8', errors='replace').replace('\u25b2', '^').replace('\u25bc', 'v')
print(output[:2000])  # Limit output

# Check if port 3000 is listening
print("\n[3] Port 3000 Status:")
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>&1 || echo "Not responding"')
print(stdout.read().decode('utf-8', errors='replace'))

# Check health endpoint
print("\n[4] Health Endpoint:")
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:3000/api/health 2>&1 | head -c 500')
print(stdout.read().decode('utf-8', errors='replace'))

# Check if container is restarting
print("\n[5] Container Restart Count:")
stdin, stdout, stderr = ssh.exec_command('docker inspect mycosoft-website --format "{{.RestartCount}}" 2>&1')
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()

print("\n" + "=" * 60)
