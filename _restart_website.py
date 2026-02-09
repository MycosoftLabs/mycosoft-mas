#!/usr/bin/env python3
"""Restart website container on sandbox - Feb 5, 2026"""
import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

# Don't wait for output - just send the command
# Use nohup to run in background
cmd = """
cd /home/mycosoft/mycosoft/mas
nohup docker compose -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website > /tmp/restart.log 2>&1 &
echo "Command sent"
"""

stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
print(stdout.read().decode())

# Check current container status
stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=website --format '{{.Names}} {{.Status}}'", timeout=10)
print("Container status:", stdout.read().decode())

ssh.close()
print("[DONE] Check container status in a few seconds")
