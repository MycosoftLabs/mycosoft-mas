#!/usr/bin/env python3
import paramiko, os
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
password = os.environ.get("VM_PASSWORD", "Mushroom1!Mushroom1!")
try:
    ssh.connect("192.168.0.187", username="mycosoft", password=password, timeout=10)
    stdin, stdout, stderr = ssh.exec_command('docker ps --format "{{.Names}} {{.Status}}"', timeout=10)
    print("SSH OK. Containers:")
    print(stdout.read().decode())
    stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:3000 -o /dev/null -w "%{http_code}"', timeout=10)
    print(f"Website HTTP: {stdout.read().decode()}")
    ssh.close()
except Exception as e:
    print(f"SSH failed: {e}")
