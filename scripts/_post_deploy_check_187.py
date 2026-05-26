#!/usr/bin/env python3
import os
from pathlib import Path

import paramiko

for fname in (Path(__file__).resolve().parents[1] / ".credentials.local",):
    if fname.exists():
        for line in fname.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"\'')

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.187", username="mycosoft", password=pw, timeout=30)

cmds = [
    'docker ps --filter name=mycosoft-website --format "{{.Names}} {{.Image}} {{.Status}}"',
    "curl -s http://localhost:3000/api/health | head -c 500",
    "test -f /opt/mycosoft/website/scripts/blue-green-deploy.sh && echo bg_script=yes || echo bg_script=no",
]
for c in cmds:
    print(">>>", c)
    _, stdout, _ = ssh.exec_command(c, timeout=30)
    print(stdout.read().decode(errors="replace"))
ssh.close()
