#!/usr/bin/env python3
"""Full rebuild and deploy of the website to the VM."""
import paramiko
import time

def run_cmd(client, cmd, name, timeout=120):
    """Run a command and print output."""
    print(f"\n{'='*60}")
    print(f">>> {name}")
    print(f">>> {cmd}")
    print('='*60)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode()
    errors = stderr.read().decode()
    print(output)
    if errors:
        print(f"[INFO/STDERR]: {errors}")
    return output

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("="*60)
    print("FULL WEBSITE REBUILD & DEPLOY")
    print("="*60)
    print("\nConnecting to VM 192.168.0.187...")
    client.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)
    print("Connected!\n")
    
    # Step 1: Check current git status or clone fresh
    run_cmd(client, 'ls -la /home/mycosoft/mycosoft/', 'Check mycosoft directory')
    
    # Step 2: Pull latest website code
    run_cmd(client, '''
        cd /home/mycosoft/mycosoft/website && \
        git fetch origin && \
        git reset --hard origin/main && \
        git log --oneline -3
    ''', 'Pull latest website code')
    
    # Step 3: Stop the old container
    run_cmd(client, 'docker stop mycosoft-website 2>/dev/null || echo "Container not running"', 'Stop old container')
    
    # Step 4: Remove old container
    run_cmd(client, 'docker rm mycosoft-website 2>/dev/null || echo "Container not found"', 'Remove old container')
    
    # Step 5: Rebuild the Docker image (no cache)
    print("\n" + "="*60)
    print(">>> REBUILDING DOCKER IMAGE (this may take a few minutes)...")
    print("="*60)
    run_cmd(client, '''
        cd /home/mycosoft/mycosoft/website && \
        docker build -t website-website:latest --no-cache .
    ''', 'Build new Docker image', timeout=600)
    
    # Step 6: Start the new container
    run_cmd(client, '''
        cd /home/mycosoft/mycosoft/website && \
        docker compose up -d
    ''', 'Start new container')
    
    # Step 7: Wait and check health
    print("\n>>> Waiting 10 seconds for container to start...")
    time.sleep(10)
    
    run_cmd(client, 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep website', 'Check container status')
    
    # Step 8: Check logs
    run_cmd(client, 'docker logs mycosoft-website --tail 20', 'Check container logs')
    
    client.close()
    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE!")
    print("="*60)
    print("\nPlease verify at: https://sandbox.mycosoft.com/devices/mushroom-1")

if __name__ == "__main__":
    main()
