#!/usr/bin/env python3
"""Verify full deployment and test all endpoints"""

import paramiko
import requests
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def main():
    print("=" * 60)
    print("MYCOSOFT DEPLOYMENT VERIFICATION")
    print("=" * 60)
    
    # Connect to VM
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected to VM!")
    
    # Check running containers
    print("\n1. RUNNING CONTAINERS:")
    print("-" * 40)
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker ps --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())
    
    # Check cloudflared
    print("\n2. CLOUDFLARE TUNNEL STATUS:")
    print("-" * 40)
    cmd = f"echo '{VM_PASSWORD}' | sudo -S systemctl status cloudflared --no-pager 2>/dev/null || echo 'Not a systemd service'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    if "Active:" in out:
        for line in out.split("\n"):
            if "Active:" in line or "cloudflared" in line.lower():
                print(line.strip())
    else:
        print(out[:200])
    
    # Check if cloudflared is running
    cmd = "pgrep -f cloudflared"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    pids = stdout.read().decode().strip()
    if pids:
        print(f"Cloudflared PIDs: {pids}")
    else:
        print("Cloudflared NOT running!")
    
    ssh.close()
    
    # Test local endpoints on VM
    print("\n3. LOCAL ENDPOINTS (on VM):")
    print("-" * 40)
    local_endpoints = [
        ("Website", f"http://{VM_IP}:3000"),
        ("MINDEX API", f"http://{VM_IP}:8000/api/mindex/health"),
        ("MycoBrain", f"http://{VM_IP}:8003/health"),
        ("MAS Orchestrator", f"http://{VM_IP}:8001/health"),
        ("n8n", f"http://{VM_IP}:5678"),
        ("MYCA Dashboard", f"http://{VM_IP}:3100"),
        ("Grafana", f"http://{VM_IP}:3002"),
    ]
    
    for name, url in local_endpoints:
        try:
            r = requests.get(url, timeout=5)
            print(f"  {name}: {r.status_code}")
        except Exception as e:
            print(f"  {name}: ERROR - {str(e)[:50]}")
    
    # Test Cloudflare tunnel endpoints
    print("\n4. CLOUDFLARE TUNNEL ENDPOINTS:")
    print("-" * 40)
    cf_endpoints = [
        ("sandbox.mycosoft.com", "https://sandbox.mycosoft.com"),
        ("api-sandbox.mycosoft.com", "https://api-sandbox.mycosoft.com"),
        ("brain-sandbox.mycosoft.com", "https://brain-sandbox.mycosoft.com"),
    ]
    
    for name, url in cf_endpoints:
        try:
            r = requests.get(url, timeout=10)
            content_type = r.headers.get('content-type', 'unknown')
            print(f"  {name}: {r.status_code} ({content_type[:30]})")
        except Exception as e:
            print(f"  {name}: ERROR - {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
