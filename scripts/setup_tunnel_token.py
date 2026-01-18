#!/usr/bin/env python3
"""Install Cloudflare Tunnel with token on VM"""
import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

# Your Cloudflare tunnel token
TUNNEL_TOKEN = "eyJhIjoiYzMwZmFmODdhZmYxNGE5YTc1YWQ5ZWZhNWE0MzJmMzciLCJ0IjoiYmQzODUzMTMtYTQ0YS00N2FlLThmOGEtNTgxNjA4MTE4MTI3IiwicyI6IlpEUTJNbVl6TWpFdE9ERTBOeTAwWlRJeExUaGpaV010WXpJNU5tUXpNMlV6TVRoaiJ9"

print("=" * 60)
print("INSTALLING CLOUDFLARE TUNNEL WITH TOKEN")
print(f"VM: {VM_IP}")
print("=" * 60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
print("Connected!")

# Install cloudflared service with token
print("\n>>> Installing cloudflared service with token...")
cmd = f"echo '{VM_PASS}' | sudo -S cloudflared service install {TUNNEL_TOKEN}"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
print("STDOUT:", stdout.read().decode())
err = stderr.read().decode()
if err and 'password' not in err.lower():
    print("STDERR:", err)

# Enable and start the service
print("\n>>> Enabling and starting cloudflared service...")
cmd2 = f"echo '{VM_PASS}' | sudo -S systemctl enable --now cloudflared"
stdin, stdout, stderr = ssh.exec_command(cmd2, timeout=30)
print("STDOUT:", stdout.read().decode())
err = stderr.read().decode()
if err and 'password' not in err.lower():
    print("STDERR:", err)

# Check status
print("\n>>> Checking service status...")
cmd3 = f"echo '{VM_PASS}' | sudo -S systemctl status cloudflared --no-pager"
stdin, stdout, stderr = ssh.exec_command(cmd3, timeout=30)
status = stdout.read().decode()
print(status)

ssh.close()

if "active (running)" in status.lower():
    print("\n" + "=" * 60)
    print("SUCCESS! Cloudflare tunnel is running!")
    print("=" * 60)
    print("\nNow go to Cloudflare Dashboard and add public hostname routes:")
    print("  sandbox.mycosoft.com -> http://localhost:3000")
    print("  api-sandbox.mycosoft.com -> http://localhost:8000")
else:
    print("\nTunnel may need configuration. Check Cloudflare dashboard.")
