#!/usr/bin/env python3
"""Fix Cloudflare cache issue by recreating the tunnel connection"""

import paramiko
import time
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")
    
    # Check cloudflared version
    print("\n1. Cloudflared version:")
    out, _ = run_sudo(ssh, "cloudflared --version")
    print(f"   {out.strip()}")
    
    # Check cloudflared logs for errors
    print("\n2. Recent cloudflared logs (checking for errors):")
    out, _ = run_sudo(ssh, "journalctl -u cloudflared --no-pager -n 30 2>&1 | grep -iE 'error|fail|404|timeout' | tail -10")
    if out.strip():
        print(out)
    else:
        print("   No errors found in recent logs")
    
    # Stop cloudflared completely
    print("\n3. Stopping cloudflared completely...")
    out, _ = run_sudo(ssh, "systemctl stop cloudflared")
    print("   Stopped")
    time.sleep(3)
    
    # Clear any cloudflared cache
    print("\n4. Clearing cloudflared cache...")
    out, _ = run_sudo(ssh, "rm -rf /root/.cloudflared/*.json 2>/dev/null; rm -rf /home/mycosoft/.cloudflared/*.json 2>/dev/null; echo 'Cleared'")
    print(f"   {out.strip()}")
    
    # Restart cloudflared
    print("\n5. Starting cloudflared fresh...")
    out, _ = run_sudo(ssh, "systemctl start cloudflared")
    print("   Started")
    time.sleep(5)
    
    # Check status
    print("\n6. Cloudflared status:")
    out, _ = run_sudo(ssh, "systemctl status cloudflared --no-pager 2>&1 | head -5")
    print(out)
    
    # Test local access
    print("\n7. Testing local access (VM localhost):")
    test_urls = [
        "http://localhost:3000/_next/static/css/40f35a41b2e2f0e8.css",
        "http://localhost:3000/_next/static/chunks/webpack-624e62a1215c0b8e.js",
    ]
    for url in test_urls:
        stdin, stdout, stderr = ssh.exec_command(
            f"curl -s -o /dev/null -w '%{{http_code}} %{{size_download}}' '{url}'"
        )
        result = stdout.read().decode().strip()
        filename = url.split('/')[-1]
        print(f"   {filename}: {result}")
    
    ssh.close()
    print("\n8. Wait 30 seconds then try the website again...")
    print("   The Cloudflare edge cache may take a minute to refresh.")
    print("\n   Alternatively, try purging the Cloudflare cache from the dashboard:")
    print("   - Go to Cloudflare Dashboard > sandbox.mycosoft.com > Caching")
    print("   - Click 'Purge Everything' or purge specific URLs")

if __name__ == "__main__":
    main()
