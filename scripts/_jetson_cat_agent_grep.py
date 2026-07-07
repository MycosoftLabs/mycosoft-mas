#!/usr/bin/env python3
import os
from pathlib import Path
import paramiko

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
for line in creds.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()
pw = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.123", username="jetson", password=pw, timeout=15)
_, stdout, _ = ssh.exec_command(
    "grep -n -E 'PCA9685|pca9685|0x40|I2C' "
    "/home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py | head -40",
    timeout=30,
)
print(stdout.read().decode())
ssh.close()
