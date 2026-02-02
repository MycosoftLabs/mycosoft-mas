#!/usr/bin/env python3
"""Deploy to sandbox VM via SSH"""
import paramiko
import sys

def run_command(client, cmd):
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f"STDERR: {err}")
    return out, err

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("Connecting to sandbox VM (192.168.0.187)...")
        client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
        print("Connected!")
        
        # Correct paths
        website_repo = "/opt/mycosoft/website"
        mas_repo = "/home/mycosoft/mycosoft/mas"
        compose_dir = "/opt/mycosoft"
        
        # Pull MAS updates
        print("\n=== Updating MAS repo ===")
        run_command(client, f"cd {mas_repo} && git fetch origin")
        run_command(client, f"cd {mas_repo} && git reset --hard origin/main")
        run_command(client, f"cd {mas_repo} && git log --oneline -3")
        
        # Pull Website updates  
        print("\n=== Updating Website repo ===")
        run_command(client, f"cd {website_repo} && git fetch origin")
        run_command(client, f"cd {website_repo} && git reset --hard origin/main")
        run_command(client, f"cd {website_repo} && git log --oneline -3")
        
        # Rebuild image - code is baked into container
        print("\n=== Rebuilding website image (this takes 2-5 minutes) ===")
        # Use nohup to prevent timeout, then check status
        stdin, stdout, stderr = client.exec_command(
            f"cd {website_repo} && nohup docker build -t website-website:latest --no-cache . > /tmp/docker-build.log 2>&1 && echo BUILD_DONE || echo BUILD_FAILED",
            timeout=600
        )
        result = stdout.read().decode().strip()
        print(f"Build result: {result}")
        
        # Show last 20 lines of build log
        run_command(client, "tail -20 /tmp/docker-build.log")
        
        # Restart container
        print("\n=== Restarting website container ===")
        run_command(client, f"cd {compose_dir} && docker compose restart mycosoft-website")
        
        # Check status
        print("\n=== Container Status ===")
        run_command(client, "docker ps --filter 'name=mycosoft' --format 'table {{.Names}}\t{{.Status}}'")
        
        print("\n=== Deployment Complete! ===")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
