#!/usr/bin/env python3
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

print('=== Docker Container Status ===')
cmd = "echo 'REDACTED_VM_SSH_PASSWORD' | sudo -S docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

print('=== Testing localhost:3000 ===')
cmd2 = 'curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo FAILED'
stdin, stdout, stderr = ssh.exec_command(cmd2)
print('Port 3000:', stdout.read().decode())

print('=== Testing localhost:8000 ===')
cmd3 = 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null || echo FAILED'
stdin, stdout, stderr = ssh.exec_command(cmd3)
print('Port 8000:', stdout.read().decode())

print('=== Testing localhost:8003 ===')
cmd4 = 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8003 2>/dev/null || echo FAILED'
stdin, stdout, stderr = ssh.exec_command(cmd4)
print('Port 8003:', stdout.read().decode())

print('=== Listening ports ===')
cmd5 = "ss -tlnp | grep -E '3000|8000|8003'"
stdin, stdout, stderr = ssh.exec_command(cmd5)
print(stdout.read().decode())

ssh.close()
