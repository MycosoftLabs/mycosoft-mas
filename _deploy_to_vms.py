#!/usr/bin/env python3
"""
Deploy to MAS VM and Website Sandbox VM
February 3, 2026
"""

import paramiko
import time

def run_ssh_command(host, user, password, command, timeout=120):
    """Execute SSH command with password authentication."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=30)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        client.close()
        return exit_code == 0, out + err
    except Exception as e:
        return False, str(e)

def main():
    password = "Mushroom1!Mushroom1!"
    
    # Deploy to MAS VM
    print("=" * 60)
    print("Deploying to MAS VM (192.168.0.188)...")
    print("=" * 60)
    
    success, output = run_ssh_command(
        "192.168.0.188",
        "mycosoft",
        password,
        "cd /opt/mycosoft/mas && git fetch origin && git reset --hard origin/main"
    )
    print(f"Git pull: {'SUCCESS' if success else 'FAILED'}")
    print(output[:1000] if output else "No output")
    
    if success:
        # Restart orchestrator
        print("\nRestarting myca-orchestrator...")
        success2, output2 = run_ssh_command(
            "192.168.0.188",
            "mycosoft",
            password,
            "cd /opt/mycosoft/mas && docker compose restart myca-orchestrator 2>&1 || echo 'Container restart skipped'"
        )
        print(f"Orchestrator restart: {'SUCCESS' if success2 else 'SKIPPED'}")
        print(output2[:500] if output2 else "No output")
    
    # Deploy to Website Sandbox VM
    print("\n" + "=" * 60)
    print("Deploying to Website Sandbox VM (192.168.0.187)...")
    print("=" * 60)
    
    success, output = run_ssh_command(
        "192.168.0.187",
        "mycosoft",
        password,
        "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main"
    )
    print(f"Git pull: {'SUCCESS' if success else 'FAILED'}")
    print(output[:1000] if output else "No output")
    
    if success:
        # Rebuild website container
        print("\nRebuilding website container (this may take a few minutes)...")
        success2, output2 = run_ssh_command(
            "192.168.0.187",
            "mycosoft",
            password,
            "cd /opt/mycosoft/website && docker build -t website-website:latest . 2>&1 | tail -20",
            timeout=300
        )
        print(f"Docker build: {'SUCCESS' if success2 else 'FAILED'}")
        print(output2[-1000:] if output2 else "No output")
        
        # Restart container
        print("\nRestarting website container...")
        success3, output3 = run_ssh_command(
            "192.168.0.187",
            "mycosoft",
            password,
            "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; docker run -d --name mycosoft-website -p 3000:3000 -v /opt/mycosoft/media/website/assets:/app/public/assets:ro --restart unless-stopped website-website:latest"
        )
        print(f"Container restart: {'SUCCESS' if success3 else 'FAILED'}")
        print(output3[:500] if output3 else "No output")
    
    print("\n" + "=" * 60)
    print("Deployment complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
