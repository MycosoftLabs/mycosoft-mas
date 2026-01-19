#!/usr/bin/env python3
"""Run website container directly from existing image."""
import paramiko
import time

def run(client, cmd, timeout=60):
    print(f"\n>>> {cmd}")
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
    client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
    print("Connected!\n")
    
    # Check existing images
    run(client, 'docker images | grep website')
    
    # Remove any existing container
    run(client, 'docker rm -f mycosoft-website 2>/dev/null || true')
    
    # Run container directly from existing image
    print("\n>>> Starting website container directly...")
    run(client, '''docker run -d \\
        --name mycosoft-website \\
        -p 3000:3000 \\
        --restart unless-stopped \\
        -e NODE_ENV=production \\
        website-website:latest''', timeout=30)
    
    print("\n>>> Waiting 15 seconds for startup...")
    time.sleep(15)
    
    # Check status
    run(client, 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "website|NAMES"')
    
    # Check logs
    print("\n>>> Container logs:")
    run(client, 'docker logs mycosoft-website --tail 30 2>&1')
    
    # Test endpoints
    print("\n>>> Testing endpoints...")
    run(client, 'curl -s -o /dev/null -w "localhost:3000 = %{http_code}\\n" http://localhost:3000/')
    run(client, 'curl -s -o /dev/null -w "/devices/mushroom-1 = %{http_code}\\n" http://localhost:3000/devices/mushroom-1')
    
    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
