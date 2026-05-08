"""Run docker builder + image prune on MINDEX VM 189 only (frees build cache)."""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
for base in (ROOT, ROOT.parent / "WEBSITE" / "website"):
    p = base / ".credentials.local"
    if p.is_file():
        for line in p.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        break

PW = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""


def main() -> int:
    if not PW:
        print("no VM_PASSWORD", file=sys.stderr)
        return 1
    b64 = base64.b64encode(PW.encode()).decode("ascii")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.189", username="mycosoft", password=PW, timeout=45)
    cmd = (
        f"echo {b64} | base64 -d | sudo -S sh -c 'docker builder prune -af; docker image prune -af; "
        "journalctl --vacuum-size=200M 2>/dev/null; df -h /'"
    )
    _, o, e = c.exec_command(cmd, timeout=600)
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    print(out[-10000:] if len(out) > 10000 else out)
    if err.strip():
        print(err[-3000:], file=sys.stderr)
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
