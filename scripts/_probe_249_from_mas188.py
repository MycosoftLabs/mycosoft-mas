"""SSH 188, curl 249:8220/health — see if hang is PC-only."""
import os
from pathlib import Path

import paramiko

root = Path(__file__).resolve().parent.parent
for line in (root / ".credentials.local").read_text(encoding="utf-8", errors="replace").splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=25)
_, o, e = c.exec_command(
    "curl -sS -m 12 http://192.168.0.249:8220/health 2>&1; echo EXIT:$?",
    timeout=20,
)
print((o.read() + e.read()).decode())
c.close()
