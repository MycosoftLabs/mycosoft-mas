#!/usr/bin/env python3
"""Rebuild website on VM with Node 18 Dockerfile."""
import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("=" * 60)
    print("  REBUILDING WEBSITE WITH NODE 18")
    print("=" * 60)
    
    print("\nConnecting to VM 192.168.0.187...")
    client.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)
    print("Connected!")
    
    commands = [
        ("Pull latest code", "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main"),
        ("Check Dockerfile", "cat /opt/mycosoft/website/Dockerfile.production | head -15"),
        ("Stop container", "docker stop mycosoft-website 2>/dev/null || true"),
        ("Remove container", "docker rm mycosoft-website 2>/dev/null || true"),
        ("Build image (this takes ~5 min)", "cd /opt/mycosoft/website && docker build -t website-website:latest -f Dockerfile.production . 2>&1"),
        ("Start container", "docker run -d --name mycosoft-website -p 3000:3000 --restart unless-stopped website-website:latest"),
        ("Check status", "docker ps | grep website"),
        ("Wait for startup", "sleep 10"),
        ("Test endpoint", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/devices/mushroom-1"),
    ]
    
    for name, cmd in commands:
        print(f"\n[{name}]")
        print(f">>> {cmd[:80]}...")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=600)  # 10 min timeout for build
        stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='replace')
        errors = stderr.read().decode('utf-8', errors='replace')
        
        # Print last 50 lines of output for long commands
        lines = output.strip().split('\n')
        if len(lines) > 50:
            print(f"... ({len(lines)-50} lines omitted) ...")
            print('\n'.join(lines[-50:]))
        else:
            print(output)
        
        if errors and 'warning' not in errors.lower():
            print(f"[INFO] {errors[:500]}")
    
    client.close()
    
    print("\n" + "=" * 60)
    print("  REBUILD COMPLETE!")
    print("=" * 60)
    print("\nTest: https://sandbox.mycosoft.com/devices/mushroom-1")
    print("Expected: $2,000 price, videos, waterfall section")

if __name__ == "__main__":
    main()
