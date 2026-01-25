#!/usr/bin/env python3
"""
Fix symlink and deploy website to sandbox VM via SSH.
"""

import paramiko
import sys
import time

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PORT = 22
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def run_ssh_commands():
    """Connect to VM and run deployment commands."""
    
    print(f"Connecting to {VM_USER}@{VM_HOST}...")
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect with password
        client.connect(
            hostname=VM_HOST,
            port=VM_PORT,
            username=VM_USER,
            password=VM_PASSWORD,
            timeout=30
        )
        print("Connected!")
        
        commands = [
            # Step 1: Create symlink
            "echo '=== Step 1: Creating symlink ===' && mkdir -p /home/mycosoft/WEBSITE && ln -sf /home/mycosoft/mycosoft/website /home/mycosoft/WEBSITE/website && ls -la /home/mycosoft/WEBSITE/",
            
            # Step 2: Clean Docker
            "echo '=== Step 2: Cleaning Docker ===' && docker system prune -f && docker builder prune -f",
            
            # Step 3: Pull latest code
            "echo '=== Step 3: Pulling latest code ===' && cd /home/mycosoft/mycosoft/website && git fetch origin main && git reset --hard origin/main",
            
            # Step 4: Build website
            "echo '=== Step 4: Building website (this takes a few minutes) ===' && cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache",
            
            # Step 5: Start container
            "echo '=== Step 5: Starting container ===' && cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website",
            
            # Step 6: Verify
            "echo '=== Step 6: Verifying ===' && docker ps | grep website && echo '' && echo 'Container logs:' && docker logs mycosoft-always-on-mycosoft-website-1 --tail 10"
        ]
        
        for cmd in commands:
            print(f"\n{'='*60}")
            print(f"Running: {cmd[:80]}...")
            print('='*60)
            
            stdin, stdout, stderr = client.exec_command(cmd, timeout=600)  # 10 min timeout for build
            
            # Stream output
            for line in stdout:
                print(line.strip())
            
            # Check for errors
            err = stderr.read().decode()
            if err:
                print(f"STDERR: {err}")
            
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                print(f"WARNING: Command exited with status {exit_status}")
        
        print("\n" + "="*60)
        print("DEPLOYMENT COMPLETE!")
        print("="*60)
        print("\nNext steps:")
        print("1. Purge Cloudflare cache at dash.cloudflare.com")
        print("2. Verify at https://sandbox.mycosoft.com/devices/mushroom-1")
        
    except paramiko.AuthenticationException:
        print("ERROR: SSH authentication failed. Check SSH keys.")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"ERROR: SSH connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    run_ssh_commands()
