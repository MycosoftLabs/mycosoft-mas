#!/usr/bin/env python3
"""Restart cloudflared service on VM"""

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")
    
    # Check cloudflared status
    print("\n1. Current cloudflared status:")
    out, err = run_sudo(ssh, "systemctl status cloudflared --no-pager 2>&1 | head -10")
    print(out)
    
    # Restart cloudflared
    print("\n2. Restarting cloudflared...")
    out, err = run_sudo(ssh, "systemctl restart cloudflared")
    print(f"   {out or 'Restarted'}")
    
    import time
    time.sleep(5)
    
    # Check new status
    print("\n3. New cloudflared status:")
    out, err = run_sudo(ssh, "systemctl status cloudflared --no-pager 2>&1 | head -10")
    print(out)
    
    # Test access
    print("\n4. Testing direct access to static files:")
    test_files = [
        "/_next/static/css/40f35a41b2e2f0e8.css",
        "/_next/static/css/5160586124011305.css",
        "/_next/static/chunks/webpack-624e62a1215c0b8e.js",
    ]
    for f in test_files:
        stdin, stdout, stderr = ssh.exec_command(
            f"curl -s -o /dev/null -w '%{{http_code}}' 'http://localhost:3000{f}'"
        )
        code = stdout.read().decode().strip()
        print(f"   {f}: {code}")
    
    ssh.close()
    print("\nDone! Try refreshing the sandbox page now.")

if __name__ == "__main__":
    main()
