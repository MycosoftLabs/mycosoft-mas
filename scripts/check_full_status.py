#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!')

print('=== All Docker Containers ===')
cmd = "echo 'Mushroom1!Mushroom1!' | sudo -S docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

print('=== Testing Services ===')
for port in [3000, 8000, 8001, 8003, 5678, 3002, 6333]:
    cmd = f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:{port} 2>/dev/null || echo FAIL'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read().decode().strip()
    status = 'OK' if result == '200' else result
    print(f'  Port {port}: {status}')

ssh.close()
