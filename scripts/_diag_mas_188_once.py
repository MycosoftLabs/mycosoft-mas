#!/usr/bin/env python3
"""One-shot MAS VM diagnostics for 188. Uses .credentials.local."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
creds_file = root / ".credentials.local"
if not creds_file.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in creds_file.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
if not pw:
    print("ERROR: no VM password")
    sys.exit(1)

import paramiko

host = "192.168.0.188"
user = "mycosoft"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw, timeout=30)

cmds = [
    ("docker ps -a --filter name=myca",),
    ("ss -tlnp 2>/dev/null | grep 8001 || true; echo '---'; netstat -tlnp 2>/dev/null | grep 8001 || true",),
    ("systemctl is-active mas-orchestrator 2>/dev/null; systemctl status mas-orchestrator --no-pager -l 2>&1 | head -40",),
    ("curl -v -m 12 http://127.0.0.1:8001/health 2>&1 | tail -25",),
    ("docker exec myca-orchestrator-new curl -s -m 8 -w '\\nHTTP:%{http_code}\\n' http://127.0.0.1:8000/health 2>&1 || echo DOCKER_EXEC_FAIL",),
    ("docker logs --tail 40 myca-orchestrator-new 2>&1",),
]

for (cmd,) in cmds:
    print(f"\n=== {cmd[:70]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print("STDERR:", err)
    print(f"[exit {rc}]")

ssh.close()
