#!/usr/bin/env python3
"""
Deploy to sandbox.mycosoft.com via SSH using Paramiko
"""
import paramiko
import time
import sys

# Configuration
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def run_command(ssh, command, timeout=300):
    """Run command and return output"""
    print(f"\n>>> {command}")
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='replace')
        errors = stderr.read().decode('utf-8', errors='replace')
        
        if output:
            print(output[:2000])
        if errors and exit_code != 0:
            print(f"STDERR: {errors[:500]}")
        
        return exit_code, output, errors
    except Exception as e:
        print(f"ERROR: {e}")
        return -1, "", str(e)

def main():
    print("=" * 60)
    print("  MYCOSOFT SANDBOX DEPLOYMENT VIA PARAMIKO SSH")
    print("=" * 60)
    
    # Connect
    print(f"\n[1] Connecting to {VM_USER}@{VM_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("    Connected successfully!")
    except Exception as e:
        print(f"    Connection failed: {e}")
        return 1
    
    # Deployment commands
    print("\n[2] Running deployment commands...")
    
    commands = [
        # Pull latest website code
        ("Pull latest website code", "cd /opt/mycosoft/website && git fetch origin main && git reset --hard origin/main"),
        
        # Show the main compose file
        ("Show main docker-compose", "head -100 /opt/mycosoft/docker-compose.yml"),
        
        # Rebuild website from main compose (project: mycosoft-production)
        ("Rebuild website container", "cd /opt/mycosoft && docker compose -p mycosoft-production build mycosoft-website --no-cache 2>&1 | tail -20"),
        
        # Restart website
        ("Restart website container", "cd /opt/mycosoft && docker compose -p mycosoft-production up -d mycosoft-website 2>&1"),
        
        # Check MINDEX
        ("Check MINDEX status", "docker exec mindex-api curl -s http://localhost:8000/health 2>/dev/null | head -c 200 || echo 'MINDEX API check failed'"),
        
        # Restart Cloudflare
        ("Restart Cloudflare tunnel", "echo 'Mushroom1!Mushroom1!' | sudo -S systemctl restart cloudflared 2>&1"),
        
        # Verify
        ("Final container status", "docker ps --format 'table {{.Names}}\\t{{.Status}}'"),
        
        # Test website
        ("Test website health", "sleep 5 && curl -s http://localhost:3000/api/health 2>/dev/null | head -c 300 || echo 'Website health check pending'"),
    ]
    
    for i, (desc, cmd) in enumerate(commands, 1):
        print(f"\n--- Step {i}/{len(commands)}: {desc} ---")
        exit_code, output, errors = run_command(ssh, cmd, timeout=600)
        if exit_code != 0 and "skip" not in cmd.lower() and "|| echo" not in cmd:
            print(f"    Warning: Command returned exit code {exit_code}")
    
    # Close connection
    ssh.close()
    
    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print("\nTest these URLs:")
    print("  - https://sandbox.mycosoft.com")
    print("  - https://sandbox.mycosoft.com/admin")
    print("  - https://sandbox.mycosoft.com/natureos")
    print("  - https://sandbox.mycosoft.com/natureos/devices")
    print("\nDon't forget to clear Cloudflare cache:")
    print("  https://dash.cloudflare.com -> mycosoft.com -> Caching -> Purge Everything")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
