#!/usr/bin/env python3
r"""
On Sandbox 192.168.0.187: pull website repo to origin/main, docker build
ghcr.io/mycosoftlabs/website:production:latest, force-recreate blue+green.
Then merge LAN + Legion env via ensure_sandbox_lan_api_urls (run separately or inline).

Long-running: docker build may take 15–30 minutes.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    raise SystemExit(2)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VM = "192.168.0.187"
WEBSITE = "/opt/mycosoft/website"
CF = "-f docker-compose.production.yml -f docker-compose.production.blue-green.yml"


def load_pw() -> str:
    root = Path(__file__).resolve().parent.parent
    for p in (root / ".credentials.local", root.parent.parent / "WEBSITE" / "website" / ".credentials.local"):
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not pw:
        raise SystemExit("VM_PASSWORD not set")
    return pw


def run(
    c: paramiko.SSHClient, cmd: str, timeout: int = 2400
) -> tuple[int, str, str]:
    _, o, e = c.exec_command(cmd, timeout=timeout)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    return o.channel.recv_exit_status(), out, err


def main() -> int:
    pw = load_pw()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(VM, username="mycosoft", password=pw, timeout=40)
    try:
        print("=== git pull ===")
        code, o, e = run(
            c,
            f"cd {WEBSITE} && git fetch origin && git reset --hard origin/main && git log -1 --oneline",
            timeout=120,
        )
        print(o, e, "exit", code)
        if code != 0:
            return code

        print("=== docker build (15–30 min) ===", flush=True)
        t0 = time.time()
        code, o, e = run(
            c,
            f"cd {WEBSITE} && docker build -t ghcr.io/mycosoftlabs/website:production-latest . 2>&1",
            timeout=2400,
        )
        print(f"build exit {code} in {time.time() - t0:.0f}s")
        print((o + e)[-8000:])

        print("=== compose up website-blue website-green ===", flush=True)
        code2, o2, e2 = run(
            c,
            f"cd {WEBSITE} && docker compose {CF} up -d --no-deps --force-recreate website-blue website-green 2>&1",
            timeout=600,
        )
        print(o2, e2, "exit", code2)

        time.sleep(8)
        _, h, _ = run(
            c,
            "curl -sS -m 20 http://127.0.0.1:3000/api/health 2>&1 | head -c 400",
            timeout=35,
        )
        print("health:", h)

        if code != 0 or code2 != 0:
            return 1
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
