#!/usr/bin/env python3
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

print('=== Current container status ===')
cmd = 'echo REDACTED_VM_SSH_PASSWORD | sudo -S docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

print('=== Files in /opt/mycosoft ===')
cmd2 = 'ls -la /opt/mycosoft/'
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

print('=== Website dir ===')
cmd3 = 'ls /opt/mycosoft/website/ 2>/dev/null | head -20 || echo "No website dir"'
stdin, stdout, stderr = ssh.exec_command(cmd3)
print(stdout.read().decode())

print('=== MAS dir ===')
cmd4 = 'ls /opt/mycosoft/mas/ 2>/dev/null | head -20 || echo "No MAS dir"'
stdin, stdout, stderr = ssh.exec_command(cmd4)
print(stdout.read().decode())

print('=== Home mycosoft dir ===')
cmd5 = 'ls ~/mycosoft/ 2>/dev/null | head -20 || echo "No home dir"'
stdin, stdout, stderr = ssh.exec_command(cmd5)
print(stdout.read().decode())

ssh.close()
