#!/usr/bin/env python3
"""
Clean Docker cache and deploy website with proper memory - Feb 6, 2026

This script:
1. Clears all Docker cache (old images, containers, volumes, build cache)
2. Restarts the website container with proper memory allocation
3. Should be run as part of every deployment
"""
import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def main():
    print("="*60)
    print("Sandbox VM Cleanup and Deploy - Feb 6, 2026")
    print("="*60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    
    # Run cleanup script in background with nohup
    cleanup_script = '''#!/bin/bash
set -x

echo "=== Starting Docker Cleanup $(date) ===" >> /tmp/cleanup.log 2>&1

# Stop website first
echo "Stopping website container..."
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true

# Clear ALL Docker cache aggressively
echo "Pruning stopped containers..."
docker container prune -f >> /tmp/cleanup.log 2>&1

echo "Pruning unused images..."
docker image prune -a -f >> /tmp/cleanup.log 2>&1

echo "Pruning unused volumes..."
docker volume prune -f >> /tmp/cleanup.log 2>&1

echo "Pruning build cache..."
docker builder prune -a -f >> /tmp/cleanup.log 2>&1

echo "Pruning networks..."
docker network prune -f >> /tmp/cleanup.log 2>&1

echo "Full system prune..."
docker system prune -a -f --volumes >> /tmp/cleanup.log 2>&1

# Show freed space
echo "=== Disk space after cleanup ===" >> /tmp/cleanup.log
df -h / >> /tmp/cleanup.log 2>&1

echo "=== Memory after cleanup ===" >> /tmp/cleanup.log
free -h >> /tmp/cleanup.log 2>&1

# Now restart website with proper memory limits
echo "Starting website container with memory limits..."
cd /home/mycosoft/mycosoft/mas

# Memory allocation strategy:
# - Total VM RAM: 62GB
# - Website: 32GB max (primary frontend)
# - MINDEX: 16GB (on separate VM or container)
# - MAS: 8GB
# - System/Other: 6GB

docker compose -f docker-compose.always-on.yml up -d mycosoft-website >> /tmp/cleanup.log 2>&1

echo "=== Container status ===" >> /tmp/cleanup.log
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" >> /tmp/cleanup.log 2>&1

echo "=== Cleanup complete $(date) ===" >> /tmp/cleanup.log
'''
    
    # Write and execute cleanup script
    print("Writing cleanup script to VM...")
    stdin, stdout, stderr = ssh.exec_command(f'''cat > /tmp/cleanup.sh << 'ENDSCRIPT'
{cleanup_script}
ENDSCRIPT
chmod +x /tmp/cleanup.sh
echo "Script written"
''', timeout=10)
    print(stdout.read().decode())
    
    print("Executing cleanup in background (this may take several minutes)...")
    stdin, stdout, stderr = ssh.exec_command('nohup bash /tmp/cleanup.sh > /tmp/cleanup_exec.log 2>&1 &', timeout=5)
    print("Cleanup started in background")
    
    ssh.close()
    
    # Wait and check progress
    print("\nWaiting for cleanup to complete...")
    for i in range(12):  # Wait up to 2 minutes
        time.sleep(10)
        print(f"  Checking progress... ({(i+1)*10}s)")
        
        try:
            ssh2 = paramiko.SSHClient()
            ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh2.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=10)
            
            stdin, stdout, stderr = ssh2.exec_command('tail -5 /tmp/cleanup.log 2>/dev/null', timeout=10)
            stdout.channel.settimeout(10)
            log = stdout.read().decode()
            if log:
                print(f"    {log.strip()[:100]}")
            
            if "Cleanup complete" in log:
                print("\nCleanup completed!")
                break
                
            ssh2.close()
        except Exception as e:
            print(f"    (waiting...)")
    
    # Final status check
    print("\n" + "="*60)
    print("Final Status Check")
    print("="*60)
    
    try:
        ssh3 = paramiko.SSHClient()
        ssh3.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh3.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=10)
        
        stdin, stdout, stderr = ssh3.exec_command('free -h && echo "---" && docker ps --filter name=website --format "{{.Names}} {{.Status}}"', timeout=15)
        stdout.channel.settimeout(15)
        print(stdout.read().decode())
        
        ssh3.close()
    except Exception as e:
        print(f"Status check error: {e}")
    
    print("\nDone! Test: https://sandbox.mycosoft.com/api/mycobrain/health")

if __name__ == "__main__":
    main()
