"""Print systemd and drop-in for mas-orchestrator EARTH2 on VM 188."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parents[1]
text = (REPO / ".credentials.local").read_text(encoding="utf-8", errors="replace")
pw = ""
for line in text.splitlines():
    m = re.match(r"^\s*VM_SSH_PASSWORD\s*=\s*(.+)\s*$", line)
    if m:
        pw = m.group(1).strip().strip('"').strip("'")
        break
if not pw:
    sys.exit("no password")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=25)
for cmd in [
    "cat /etc/systemd/system/mas-orchestrator.service.d/earth2-api.conf 2>/dev/null || echo NOFILE",
    "systemctl show mas-orchestrator -p Environment --no-pager",
    "pid=$(pgrep -fo 'mycosoft_mas.core.myca_main' || pgrep -fo uvicorn || echo); "
    "if [ -n \"$pid\" ] && [ -r /proc/$pid/environ ]; then "
    "tr '\\0' '\\n' < /proc/$pid/environ | grep -E '^EARTH2_' || true; else echo NO_PROC; fi",
]:
    _, o, e = c.exec_command(cmd, timeout=30)
    print("===", cmd[:70], "===")
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
_, o, e = c.exec_command(
    "curl -sS -m 10 -w '\\nHTTP:%{http_code}' http://192.168.0.249:8220/health 2>&1",
    timeout=25,
)
print("=== curl 249:8220/health from MAS ===")
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
