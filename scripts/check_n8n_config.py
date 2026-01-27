#!/usr/bin/env python3
"""Check n8n container configuration"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!')
    
    print('=== n8n Container Environment ===')
    stdin, stdout, stderr = ssh.exec_command('docker exec myca-n8n env | grep -E "N8N|BASIC" | sort')
    print(stdout.read().decode())
    
    print('=== n8n Container Logs (last 20 lines) ===')
    stdin, stdout, stderr = ssh.exec_command('docker logs myca-n8n 2>&1 | tail -20')
    print(stdout.read().decode())
    
    print('=== Testing n8n health ===')
    stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:5678/healthz')
    print(stdout.read().decode())
    
    # Test with basic auth
    print('\n=== Testing n8n API with Basic Auth ===')
    stdin, stdout, stderr = ssh.exec_command('curl -s -u admin:Mushroom1! http://localhost:5678/api/v1/workflows | head -100')
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    main()
