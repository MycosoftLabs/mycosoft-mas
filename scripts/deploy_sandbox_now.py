#!/usr/bin/env python3
"""Quick sandbox deployment script"""
import paramiko
import sys
import time

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def run_cmd(ssh, cmd, timeout=120):
    """Run command and return output"""
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print(f"STDERR: {err}")
    return out, err

def main():
    print("=" * 60)
    print("SANDBOX DEPLOYMENT SCRIPT")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"\nConnecting to {VM_HOST}...")
        ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!")
        
        # 1. Check docker status
        run_cmd(ssh, 'docker ps --format "table {{.Names}}\t{{.Status}}" | head -15')
        
        # 2. Pull latest code
        run_cmd(ssh, 'cd /opt/mycosoft/website && git fetch origin main && git reset --hard origin/main')
        
        # 3. Check current directory structure
        run_cmd(ssh, 'ls -la /opt/mycosoft/')
        
        # 4. Rebuild website container
        print("\n" + "=" * 60)
        print("REBUILDING WEBSITE CONTAINER (this may take a few minutes)...")
        print("=" * 60)
        
        # Check which compose file exists
        out, _ = run_cmd(ssh, 'ls /opt/mycosoft/*.yml 2>/dev/null || ls /home/mycosoft/mycosoft/mas/*.yml 2>/dev/null')
        
        # Try the always-on compose file first
        run_cmd(ssh, 'cd /opt/mycosoft && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -20', timeout=600)
        
        # 5. Restart container
        print("\n" + "=" * 60)
        print("RESTARTING WEBSITE CONTAINER...")
        print("=" * 60)
        run_cmd(ssh, 'cd /opt/mycosoft && docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website')
        
        # 6. Wait and check
        print("\nWaiting 10 seconds for container to start...")
        time.sleep(10)
        run_cmd(ssh, 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(website|Website)"')
        
        # 7. Check logs
        print("\n" + "=" * 60)
        print("CONTAINER LOGS (last 20 lines):")
        print("=" * 60)
        run_cmd(ssh, 'docker logs mycosoft-always-on-mycosoft-website-1 --tail 20 2>&1 || docker logs mycosoft-website --tail 20 2>&1')
        
        # 8. Test health
        print("\n" + "=" * 60)
        print("HEALTH CHECK:")
        print("=" * 60)
        run_cmd(ssh, 'curl -s http://localhost:3000 | head -5 || echo "Website not responding"')
        
        print("\n" + "=" * 60)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Clear Cloudflare cache: https://dash.cloudflare.com -> Caching -> Purge Everything")
        print("2. Verify: https://sandbox.mycosoft.com/natureos")
        
        ssh.close()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
