#!/usr/bin/env python3
"""Update the website container on VM with the fresh image"""

import paramiko
from scp import SCPClient
import time
from pathlib import Path

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

FRESH_IMAGE = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\DOCKER_EXPORTS\website-website_fresh.tar")

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    print("="*60)
    print("UPDATING WEBSITE IMAGE ON VM")
    print("="*60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected to VM!")
    
    # Transfer fresh image
    print(f"\n1. Transferring fresh website image ({FRESH_IMAGE.stat().st_size / 1024 / 1024:.1f} MB)...")
    
    def progress(filename, size, sent):
        pct = (sent / size) * 100
        bar = "=" * int(pct/5) + ">" + " " * (20 - int(pct/5))
        print(f"\r   [{bar}] {pct:.1f}%", end="", flush=True)
    
    scp = SCPClient(ssh.get_transport(), progress=progress)
    scp.put(str(FRESH_IMAGE), "/opt/mycosoft/images/website-website_fresh.tar")
    scp.close()
    print("\n   Transfer complete!")
    
    # Stop existing website container
    print("\n2. Stopping existing website container...")
    out, err = run_sudo(ssh, "docker stop mycosoft-website")
    print(f"   {out.strip() or err.strip()}")
    
    out, err = run_sudo(ssh, "docker rm mycosoft-website")
    print(f"   Removed: {out.strip() or err.strip()}")
    
    # Remove old image
    print("\n3. Removing old website image...")
    out, err = run_sudo(ssh, "docker rmi website-website:latest 2>/dev/null || echo 'No old image'")
    print(f"   {out.strip()}")
    
    # Load new image
    print("\n4. Loading fresh website image...")
    out, err = run_sudo(ssh, "docker load -i /opt/mycosoft/images/website-website_fresh.tar")
    print(f"   {out.strip()}")
    
    # Restart the stack
    print("\n5. Restarting docker compose...")
    out, err = run_sudo(ssh, "sh -c 'cd /opt/mycosoft && docker compose up -d'")
    print(f"   {out[:200] if out else 'Started'}")
    if err:
        print(f"   Errors: {err[:200]}")
    
    # Wait for startup
    print("\n6. Waiting 30 seconds for startup...")
    time.sleep(30)
    
    # Check status
    print("\n7. Checking container status...")
    out, err = run_sudo(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'website|NAMES'")
    print(f"   {out}")
    
    # Test endpoint
    print("\n8. Testing website endpoint...")
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
    code = stdout.read().decode().strip()
    print(f"   HTTP Status: {code}")
    
    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:3000 | wc -c")
    size = stdout.read().decode().strip()
    print(f"   Content size: {size} bytes")
    
    ssh.close()
    
    print("\n" + "="*60)
    print("UPDATE COMPLETE!")
    print("="*60)
    print("\nPlease check https://sandbox.mycosoft.com in your browser")

if __name__ == "__main__":
    main()
