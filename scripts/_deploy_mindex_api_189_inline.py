"""One-shot: git pull + rebuild mindex-api on VM 189 (meshtastic routes, etc.)."""
from __future__ import annotations

import os
import sys
import time
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
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.189", username="mycosoft", password=PW, timeout=45)
    cmd = (
        "set -e; cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main && "
        "git log -1 --oneline && docker compose stop api && docker compose rm -f api && "
        "docker compose build --no-cache api && docker compose up -d --no-deps api"
    )
    _, stdout, stderr = c.exec_command(cmd, timeout=960)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    tail = 12000
    print(out[-tail:] if len(out) > tail else out)
    if err.strip():
        print(err[-tail:], file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    print("exit_code", code)
    time.sleep(12)
    _, ho, _ = c.exec_command("curl -s -m 10 http://127.0.0.1:8000/health", timeout=30)
    print("health", ho.read().decode()[:500])
    _, o2, _ = c.exec_command(
        "curl -s -m 20 http://127.0.0.1:8000/api/mindex/openapi.json | "
        "python3 -c \"import json,sys; d=json.load(sys.stdin); "
        "print('meshtastic_paths', sum(1 for k in d.get('paths',{}) if 'meshtastic' in k))\"",
        timeout=40,
    )
    print("openapi_probe", o2.read().decode().strip())
    c.close()
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
