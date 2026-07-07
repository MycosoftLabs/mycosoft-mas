#!/usr/bin/env python3
import os
import sys
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
    "sed -n '1,200p' /home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py",
    timeout=30,
)
data = stdout.read().decode("utf-8", errors="replace")
out = Path(__file__).resolve().parent / "_jetson_agent_snippet.txt"
out.write_text(data, encoding="utf-8")
print("WROTE", out)
ssh.close()
