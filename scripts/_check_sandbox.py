#!/usr/bin/env python3
import os
from pathlib import Path

import paramiko

for fname in (
    Path(__file__).resolve().parents[1] / ".credentials.local",
):
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
    "cd /opt/mycosoft/website && git status -sb",
    "cd /opt/mycosoft/website && git branch -a | head -8",
    'docker ps --filter name=mycosoft-website --format "{{.Names}} {{.Status}} {{.Image}}"',
]
for c in cmds:
    print(">>>", c)
    _, stdout, stderr = ssh.exec_command(c, timeout=60)
    print(stdout.read().decode(errors="replace")[:1000])
    err = stderr.read().decode(errors="replace")
    if err:
        print("stderr:", err[:300])
ssh.close()
