"""SSH MAS 188: git fetch + reset --hard origin/main in repo dir (no service restart)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    text = (REPO / ".credentials.local").read_text(encoding="utf-8", errors="replace")
    pw = ""
    for line in text.splitlines():
        m = re.match(r"^\s*VM_SSH_PASSWORD\s*=\s*(.+)\s*$", line)
        if m:
            pw = m.group(1).strip().strip('"').strip("'")
            break
    if not pw:
        sys.exit("VM_SSH_PASSWORD missing")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        os.environ.get("MAS_VM_IP", "192.168.0.188"),
        username=os.environ.get("VM_SSH_USER", "mycosoft"),
        password=pw,
        timeout=35,
    )
    cmd = (
        "bash -lc "
        + repr(
            "set -e; MAS_DIR=/home/mycosoft/mycosoft/mas; "
            "[ -d /opt/mycosoft/mas ] && MAS_DIR=/opt/mycosoft/mas; "
            'cd "$MAS_DIR" && git fetch origin && git reset --hard origin/main && git log -1 --oneline'
        )
    )
    _, o, e = c.exec_command(cmd, timeout=120)
    print((o.read() + e.read()).decode("utf-8", "replace"))
    c.close()


if __name__ == "__main__":
    main()
