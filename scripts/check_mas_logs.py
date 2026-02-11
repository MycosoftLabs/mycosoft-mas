#!/usr/bin/env python3
"""Check MAS container logs for Gemini API calls"""
import os
import paramiko

MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
MAS_VM_PASS = os.environ.get("VM_PASSWORD", "REDACTED_VM_SSH_PASSWORD")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)

print("=== Last 100 lines of MAS container logs ===\n")
stdin, stdout, stderr = ssh.exec_command("docker logs myca-orchestrator-new --tail 100 2>&1")
output = stdout.read().decode('utf-8', errors='ignore')

# Filter for relevant lines
for line in output.split('\n'):
    if any(keyword in line for keyword in ['gemini', 'Gemini', 'API', 'intent', 'Intent', 'ERROR', 'WARNING', 'GEMINI_API_KEY']):
        print(line)

ssh.close()
