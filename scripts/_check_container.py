#!/usr/bin/env python3
"""Check MAS container status and logs"""
import paramiko
import os

VM_IP = "192.168.0.188"
VM_USER = "mycosoft"
VM_PASS = os.environ.get("VM_PASSWORD", "Mushroom1!Mushroom1!")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

print("=== Container Status ===")
stdin, stdout, stderr = ssh.exec_command("docker ps -a --filter name=myca-orchestrator", timeout=30)
print(stdout.read().decode())

print("\n=== Container Logs ===")
stdin, stdout, stderr = ssh.exec_command("docker logs myca-orchestrator-new --tail 100 2>&1", timeout=30)
print(stdout.read().decode())

ssh.close()
