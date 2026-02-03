#!/usr/bin/env python3
"""Deploy to MAS VM - Feb 3, 2026"""
import paramiko
import sys

def deploy():
    host = "192.168.0.188"
    user = "mycosoft"
    password = "REDACTED_VM_SSH_PASSWORD"
    
    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, username=user, password=password, timeout=30)
        print("Connected!")
        
        commands = [
            "cd /home/mycosoft/mycosoft/mas && git fetch origin",
            "cd /home/mycosoft/mycosoft/mas && git reset --hard origin/main",
            "docker restart myca-orchestrator",
            "sleep 5",
            "docker ps | grep myca",
            "curl -s http://localhost:8001/health | head -1"
        ]
        
        for cmd in commands:
            print(f"\n> {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out:
                print(out)
            if err and "warning" not in err.lower():
                print(f"STDERR: {err}")
        
        print("\nDeployment complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    deploy()
