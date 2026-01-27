#!/usr/bin/env python3
"""Check and start MAS VM backend services"""

import paramiko
import sys

MAS_HOST = "192.168.0.188"
MAS_USER = "mycosoft"
MAS_PASS = "Mushroom1!Mushroom1!"

def run_command(ssh, cmd):
    """Run a command and return output"""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

def main():
    print(f"Connecting to MAS VM at {MAS_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(MAS_HOST, username=MAS_USER, password=MAS_PASS)
        print("Connected!")
        
        # Check Docker containers
        print("\n=== Docker Containers ===")
        out, err = run_command(ssh, 'docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
        print(out if out else "No containers found")
        
        # Check running processes
        print("\n=== Python/Uvicorn Processes ===")
        out, err = run_command(ssh, 'ps aux | grep -E "python|uvicorn|fastapi" | grep -v grep')
        print(out if out else "No Python processes found")
        
        # Check ports
        print("\n=== Listening Ports (8001, 8000, 5432, 6379) ===")
        out, err = run_command(ssh, 'ss -tlnp 2>/dev/null | grep -E ":8001|:8000|:5432|:6379"')
        print(out if out else "No services listening on these ports")
        
        # Check if orchestrator service exists
        print("\n=== Checking for MAS Orchestrator ===")
        out, err = run_command(ssh, 'ls -la /opt/mycosoft/mas/ 2>/dev/null | head -20')
        print(out if out else "MAS directory not found")
        
        # Check systemd service
        print("\n=== Systemd Services ===")
        out, err = run_command(ssh, 'systemctl list-units --type=service | grep -iE "myca|mas|orchestrator"')
        print(out if out else "No MAS systemd services found")
        
        ssh.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
