#!/usr/bin/env python3
"""Check MAS VM status via SSH."""
import paramiko
import os
from pathlib import Path

def load_password():
    password = os.environ.get('VM_SSH_PASSWORD') or os.environ.get('VM_PASSWORD')
    if not password:
        creds_file = Path(__file__).parent.parent / ".credentials.local"
        if creds_file.exists():
            for line in creds_file.read_text().splitlines():
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    if key.strip() in ('VM_SSH_PASSWORD', 'VM_PASSWORD'):
                        return val.strip()
    return password

def main():
    password = load_password()
    if not password:
        print("ERROR: No password found")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("Connecting to MAS VM (192.168.0.188)...")
        ssh.connect('192.168.0.188', username='mycosoft', password=password, timeout=15)
        
        commands = [
            ('MAS Service Status', 'sudo systemctl status mas-orchestrator --no-pager -l 2>&1 | head -20'),
            ('Port 8001', 'ss -tlnp | grep 8001 || echo "Port 8001 not listening"'),
            ('Docker Containers', 'docker ps --format "table {{.Names}}\\t{{.Status}}" 2>&1 | head -10'),
        ]
        
        for title, cmd in commands:
            print(f"\n=== {title} ===")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            print(stdout.read().decode(), end='')
            err = stderr.read().decode()
            if err:
                print(f'STDERR: {err}')
        
        ssh.close()
        print("\nConnection closed.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
