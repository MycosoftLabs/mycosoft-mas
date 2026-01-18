#!/usr/bin/env python3
"""Install Cloudflared on VM"""
import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)

print("Connected! Installing cloudflared...")

# Download cloudflared
cmd1 = "curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
print(f">>> {cmd1}")
stdin, stdout, stderr = ssh.exec_command(cmd1, timeout=120)
print(stdout.read().decode())
print(stderr.read().decode())

# Install it
cmd2 = f"echo '{VM_PASS}' | sudo -S dpkg -i /tmp/cloudflared.deb"
print(">>> Installing package...")
stdin, stdout, stderr = ssh.exec_command(cmd2, timeout=60)
print(stdout.read().decode())
print(stderr.read().decode())

# Verify
cmd3 = "cloudflared --version"
print(f">>> {cmd3}")
stdin, stdout, stderr = ssh.exec_command(cmd3, timeout=30)
version = stdout.read().decode()
print(version)

ssh.close()

if version:
    print(f"\n✅ Cloudflared installed: {version.strip()}")
else:
    print("\n❌ Cloudflared installation may have failed")
