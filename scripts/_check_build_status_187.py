#!/usr/bin/env python3
import os, sys
from pathlib import Path
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for p in [Path(__file__).resolve().parents[1] / ".credentials.local"]:
    if p.exists():
        for line in p.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.187", username="mycosoft", password=os.environ.get("VM_PASSWORD", ""), timeout=30)
_, out, _ = ssh.exec_command("tail -4 /tmp/hotfix_build.log 2>/dev/null; test -f /tmp/hotfix_build.exit && cat /tmp/hotfix_build.exit || echo running", timeout=20)
print(out.read().decode("utf-8", errors="replace"))
ssh.close()
