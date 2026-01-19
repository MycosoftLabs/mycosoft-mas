#!/usr/bin/env python3
"""Quick restart of website container."""
import paramiko
import time

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting...")
    client.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)
    print("Connected!")
    
    # Restart container
    print("\n>>> Restarting container...")
    stdin, stdout, stderr = client.exec_command('docker restart mycosoft-website', timeout=60)
    print(stdout.read().decode())
    
    print("\n>>> Waiting 15 seconds...")
    time.sleep(15)
    
    # Check status
    print("\n>>> Container status:")
    stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep website', timeout=30)
    print(stdout.read().decode())
    
    # Check logs
    print("\n>>> Recent logs:")
    stdin, stdout, stderr = client.exec_command('docker logs mycosoft-website --tail 30 2>&1', timeout=30)
    print(stdout.read().decode())
    
    # Test the endpoint
    print("\n>>> Testing localhost:3000...")
    stdin, stdout, stderr = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/', timeout=30)
    status = stdout.read().decode().strip()
    print(f"HTTP Status: {status}")
    
    # Test mushroom-1 page
    print("\n>>> Testing /devices/mushroom-1...")
    stdin, stdout, stderr = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/devices/mushroom-1', timeout=30)
    status = stdout.read().decode().strip()
    print(f"HTTP Status: {status}")
    
    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
