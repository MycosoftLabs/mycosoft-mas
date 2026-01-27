#!/usr/bin/env python3
"""Check MAS VM for Metabase deployment"""

import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')
    
    # Check what containers are running
    stdin, stdout, stderr = ssh.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -25')
    print('=== Running Containers ===')
    print(stdout.read().decode())
    
    # Check disk space
    stdin, stdout, stderr = ssh.exec_command('df -h / | tail -1')
    print('=== Disk Space ===')
    print(stdout.read().decode())
    
    # Check if metabase already exists
    stdin, stdout, stderr = ssh.exec_command('docker ps -a | grep -i metabase || echo "No metabase container found"')
    print('=== Metabase Status ===')
    print(stdout.read().decode())
    
    # Check if n8n is running
    stdin, stdout, stderr = ssh.exec_command('docker ps | grep -i n8n || echo "No n8n container found"')
    print('=== n8n Status ===')
    print(stdout.read().decode())
    
    # Check available ports
    stdin, stdout, stderr = ssh.exec_command('ss -tlnp | head -15')
    print('=== Listening Ports ===')
    print(stdout.read().decode())
    
    ssh.close()
    print("Done!")

if __name__ == "__main__":
    main()
