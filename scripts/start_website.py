#!/usr/bin/env python3
"""Start website container from existing image."""
import os
import paramiko
import time

def run(client, cmd, timeout=60):
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    return out

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to VM...")
    client.connect('192.168.0.187', username='mycosoft', password=os.environ.get("VM_PASSWORD", ""), timeout=30)
    print("Connected!\n")
    
    # Check existing images
    run(client, 'docker images | grep -E "website|REPOSITORY"')
    
    # Find docker-compose file
    run(client, 'ls -la /home/mycosoft/mycosoft/website/*.yml')
    
    # Start the container using docker compose
    print("\n>>> Starting website container...")
    run(client, 'cd /home/mycosoft/mycosoft/website && docker compose up -d', timeout=120)
    
    print("\n>>> Waiting 15 seconds for startup...")
    time.sleep(15)
    
    # Check status
    run(client, 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "website|NAMES"')
    
    # Check logs
    print("\n>>> Container logs:")
    run(client, 'docker logs mycosoft-website --tail 20 2>&1')
    
    # Test endpoints
    print("\n>>> Testing endpoints...")
    run(client, 'curl -s -o /dev/null -w "localhost:3000 = %{http_code}\\n" http://localhost:3000/')
    run(client, 'curl -s -o /dev/null -w "/devices/mushroom-1 = %{http_code}\\n" http://localhost:3000/devices/mushroom-1')
    
    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
