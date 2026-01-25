#!/usr/bin/env python3
"""
Fix git permissions and deploy website
"""

import paramiko
import sys
import time
from datetime import datetime

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "•", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "HEAD": "▶"}
    print(f"[{ts}] {icons.get(level, '•')} {msg}")

def run_ssh_cmd(ssh, cmd, timeout=300):
    log(f"Running: {cmd[:80]}...", "HEAD")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:5]:
            print(f"    {line}")
    if err:
        for line in err.split('\n')[:3]:
            if 'warning' not in line.lower():
                print(f"    [stderr] {line}")
    return out, err

def main():
    print("\n" + "="*60)
    print("  FIX PERMISSIONS AND DEPLOY WEBSITE")
    print("="*60 + "\n")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        log("Connecting to VM...", "HEAD")
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
        log("Connected", "OK")
        
        # Step 1: Fix git permissions
        log("Fixing git permissions...", "HEAD")
        run_ssh_cmd(ssh, "sudo chown -R mycosoft:mycosoft /home/mycosoft/mycosoft/website/.git")
        run_ssh_cmd(ssh, "sudo chmod -R 755 /home/mycosoft/mycosoft/website/.git")
        
        # Step 2: Pull latest code
        log("Pulling latest code...", "HEAD")
        run_ssh_cmd(ssh, "cd /home/mycosoft/mycosoft/website && git fetch origin && git reset --hard origin/main")
        
        # Check commit
        out, _ = run_ssh_cmd(ssh, "cd /home/mycosoft/mycosoft/website && git log --oneline -1")
        log(f"Current commit: {out}", "OK")
        
        # Step 3: Stop any website containers
        log("Stopping current containers...", "HEAD")
        run_ssh_cmd(ssh, "docker stop mycosoft-website 2>/dev/null || true")
        run_ssh_cmd(ssh, "docker rm mycosoft-website 2>/dev/null || true")
        run_ssh_cmd(ssh, "docker stop mycosoft-always-on-mycosoft-website-1 2>/dev/null || true")
        run_ssh_cmd(ssh, "docker rm mycosoft-always-on-mycosoft-website-1 2>/dev/null || true")
        
        # Step 4: Build new image with docker compose
        log("Building new Docker image (this takes 2-4 minutes)...", "HEAD")
        out, err = run_ssh_cmd(ssh, """
            cd /home/mycosoft/mycosoft/mas && \
            docker compose -f docker-compose.always-on.yml build --no-cache mycosoft-website 2>&1
        """, timeout=600)
        
        # Step 5: Find the new image
        log("Finding new image...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker images --format '{{.Repository}}:{{.Tag}} {{.CreatedAt}}' | grep mycosoft | head -3")
        
        # Step 6: Start container from existing image
        log("Starting container...", "HEAD")
        run_ssh_cmd(ssh, """
            docker run -d \
            --name mycosoft-website \
            -p 3000:3000 \
            --restart unless-stopped \
            -v /opt/mycosoft/media:/app/public/media:ro \
            -e NODE_ENV=production \
            mycosoft-always-on-mycosoft-website:latest
        """)
        
        # Step 7: Wait for healthy
        log("Waiting for container to be healthy (60s)...", "HEAD")
        for i in range(12):
            time.sleep(5)
            out, _ = run_ssh_cmd(ssh, "docker ps --filter name=mycosoft-website --format '{{.Status}}'")
            if "Up" in out:
                log(f"Container running: {out}", "OK")
                break
            if not out:
                log("Container not started, checking logs...", "WARN")
                run_ssh_cmd(ssh, "docker logs mycosoft-website --tail 10 2>&1")
        
        # Step 8: Test
        log("Testing HTTP response...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
        log(f"HTTP: {out}", "OK" if out == "200" else "WARN")
        
        # Step 9: Test MINDEX stats
        log("Testing MINDEX stats...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "curl -s http://localhost:3000/api/natureos/mindex/stats | head -c 200")
        log(f"Stats: {out[:100]}...", "OK" if "total_taxa" in out else "WARN")
        
        ssh.close()
        
        print("\n" + "="*60)
        print("  DEPLOYMENT COMPLETE")
        print("="*60)
        print("\n  Remember to purge Cloudflare cache!")
        print("  https://dash.cloudflare.com -> mycosoft.com -> Caching -> Purge")
        print()
        
    except Exception as e:
        log(f"Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
