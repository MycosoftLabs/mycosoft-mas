#!/usr/bin/env python3
"""Check Cloudflare tunnel config on VM"""

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
    return out

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")
    
    # Check cloudflared status
    print("\n=== CLOUDFLARED SERVICE STATUS ===")
    out = run_sudo(ssh, "systemctl status cloudflared --no-pager | head -20")
    print(out)
    
    # Check cloudflared config
    print("\n=== CLOUDFLARED CONFIG ===")
    out = run_sudo(ssh, "cat /etc/cloudflared/config.yml 2>/dev/null || echo 'No config file found'")
    print(out)
    
    # Check cloudflared logs
    print("\n=== CLOUDFLARED RECENT LOGS ===")
    out = run_sudo(ssh, "journalctl -u cloudflared --no-pager -n 20 2>/dev/null || echo 'No logs'")
    print(out)
    
    # Check if there's an ingress config
    print("\n=== TUNNEL INGRESS RULES ===")
    out = run_sudo(ssh, "cat /root/.cloudflared/config.yml 2>/dev/null || echo 'No config in /root'")
    print(out)
    out = run_sudo(ssh, "cat /home/mycosoft/.cloudflared/config.yml 2>/dev/null || echo 'No config in home'")
    print(out)
    
    ssh.close()

if __name__ == "__main__":
    main()
