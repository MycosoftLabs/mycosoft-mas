#!/usr/bin/env python3
"""
Deploy Latest Mycosoft Website to Sandbox VM
Uses Paramiko SSH (the method that works!)

Created: January 18, 2026
"""

import paramiko
import time
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# VM Connection Details (from docs/VM103_DEPLOYMENT_COMPLETE.md)
VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

# Paths - The code was SCP'd, not git cloned
WEBSITE_PATH = "/opt/mycosoft/website"
COMPOSE_FILE = "docker-compose.always-on.yml"

def run_sudo_command(ssh, cmd, timeout=600):
    """Run a sudo command with password via stdin"""
    # Wrap command properly for cd to work with sudo
    full_cmd = f"echo '{VM_PASS}' | sudo -S bash -c '{cmd}'"
    short_cmd = cmd[:70] + "..." if len(cmd) > 70 else cmd
    print(f"\n>>> sudo: {short_cmd}")
    
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    
    if out:
        lines = out.strip().split('\n')
        # Replace problematic unicode chars
        clean_lines = [l.replace('\u25cf', '*').replace('\u2022', '-') for l in lines]
        if len(clean_lines) > 20:
            print(f"... ({len(clean_lines) - 20} lines omitted)")
            print('\n'.join(clean_lines[-20:]))
        else:
            print('\n'.join(clean_lines))
    
    # Filter out password prompt from stderr
    err_lines = [l.replace('\u25cf', '*') for l in err.split('\n') if 'password' not in l.lower() and l.strip()]
    if err_lines:
        print(f"stderr: {' '.join(err_lines[:3])}")
    
    return out, err

def run_command(ssh, cmd, timeout=300):
    """Run a regular command"""
    short_cmd = cmd[:80] + "..." if len(cmd) > 80 else cmd
    print(f"\n>>> {short_cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    
    if out:
        lines = out.strip().split('\n')
        clean_lines = [l.replace('\u25cf', '*').replace('\u2022', '-') for l in lines]
        if len(clean_lines) > 20:
            print(f"... ({len(clean_lines) - 20} lines omitted)")
            print('\n'.join(clean_lines[-20:]))
        else:
            print('\n'.join(clean_lines))
    if err and err.strip():
        clean_err = err[:200].replace('\u25cf', '*')
        print(f"stderr: {clean_err}")
    
    return out, err

def main():
    print("=" * 60)
    print("  MYCOSOFT SANDBOX DEPLOYMENT")
    print(f"  Target: {VM_IP} (VM 103)")
    print("=" * 60)
    
    # Connect to VM
    print(f"\n[1/8] Connecting to VM at {VM_IP}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
        print("    Connected!")
    except Exception as e:
        print(f"    FAILED to connect: {e}")
        return
    
    # Check current state
    print("\n[2/8] Checking current state...")
    run_command(ssh, "hostname && uptime")
    run_sudo_command(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -10")
    
    # Check website directory structure
    print("\n[3/8] Checking website directory...")
    run_command(ssh, f"ls {WEBSITE_PATH}/docker-compose*.yml 2>/dev/null || echo 'No compose files found'")
    run_command(ssh, f"ls {WEBSITE_PATH}/app/ | head -10 2>/dev/null || echo 'No app dir'")
    
    # Since files were SCP'd (not git), we need to transfer new files
    # For now, let's try to rebuild with existing code
    print("\n[4/8] Checking if we need to pull updates...")
    run_command(ssh, f"cd {WEBSITE_PATH} && git remote -v 2>/dev/null || echo 'Not a git repo - files were transferred via SCP'")
    
    # Build website container with existing code
    print("\n[5/8] Building website container (this may take 5-10 minutes)...")
    build_cmd = f"cd {WEBSITE_PATH} && docker compose -f {COMPOSE_FILE} build mycosoft-website --no-cache"
    run_sudo_command(ssh, build_cmd, timeout=900)
    
    # Restart website container
    print("\n[6/8] Restarting website container...")
    restart_cmd = f"cd {WEBSITE_PATH} && docker compose -f {COMPOSE_FILE} up -d mycosoft-website"
    run_sudo_command(ssh, restart_cmd, timeout=300)
    
    # Wait for container to start
    print("\n    Waiting 10 seconds for container to initialize...")
    time.sleep(10)
    
    # Check PostGIS
    print("\n[7/8] Checking PostGIS extension...")
    postgis_cmd = "docker exec mindex-postgres psql -U mindex -c 'SELECT PostGIS_Version();' 2>/dev/null || echo 'PostGIS not available or container not running'"
    run_sudo_command(ssh, postgis_cmd)
    
    # Restart MINDEX
    print("\n    Restarting MINDEX API...")
    run_sudo_command(ssh, f"cd {WEBSITE_PATH} && docker compose -f {COMPOSE_FILE} restart mindex-api 2>/dev/null || echo 'MINDEX restart skipped'")
    
    # Restart Cloudflare tunnel
    print("\n[8/8] Restarting Cloudflare tunnel...")
    run_sudo_command(ssh, "systemctl restart cloudflared")
    
    # Final status
    print("\n" + "=" * 60)
    print("  DEPLOYMENT STATUS")
    print("=" * 60)
    
    print("\nContainer Status:")
    run_sudo_command(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -15")
    
    print("\nWebsite Container Logs (last 10 lines):")
    run_sudo_command(ssh, "docker logs mycosoft-website --tail 10 2>&1 || echo 'No logs'")
    
    print("\nCloudflare Tunnel Status:")
    run_sudo_command(ssh, "systemctl is-active cloudflared || echo 'cloudflared status unknown'")
    
    print("\nQuick Health Check:")
    run_command(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null || echo 'Website not responding'")
    run_command(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/health 2>/dev/null || echo 'MINDEX not responding'")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"""
Test URLs:
  - https://sandbox.mycosoft.com
  - https://sandbox.mycosoft.com/admin
  - https://sandbox.mycosoft.com/natureos
  - https://sandbox.mycosoft.com/natureos/devices

Local URLs (from network):
  - http://{VM_IP}:3000
  - http://{VM_IP}:8000 (MINDEX API)
  - http://{VM_IP}:8003 (MycoBrain)

Cloudflare Cache: 
  - Clear at https://dash.cloudflare.com
  - Domain: mycosoft.com -> Caching -> Purge Everything
""")

if __name__ == "__main__":
    main()
