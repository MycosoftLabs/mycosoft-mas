import paramiko
import time

host = '192.168.0.188'
user = 'mycosoft'
password = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(host, username=user, password=password, timeout=30)
    
    # Check container status
    stdin, stdout, stderr = ssh.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep myca-orchestrator')
    print('Container status:')
    print(stdout.read().decode())
    
    # Health check
    stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8001/health')
    health = stdout.read().decode()
    print(f'Health check: {health}')
    
    # Check recent logs
    stdin, stdout, stderr = ssh.exec_command('docker logs myca-orchestrator-new --tail 20 2>&1')
    print('\nRecent container logs:')
    print(stdout.read().decode())
    
    ssh.close()
except Exception as e:
    print(f'Error: {e}')
