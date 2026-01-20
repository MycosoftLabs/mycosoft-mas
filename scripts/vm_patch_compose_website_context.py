#!/usr/bin/env python3
"""Patch VM always-on compose to build the website from /opt/mycosoft/website.

Reason:
The running compose file uses a relative build context `../../WEBSITE/website` from
`/home/mycosoft/mycosoft/mas`, which may point to a stale checkout and cause new
commits (like /api/mycobrain/health) to not appear in the built container.
"""

from __future__ import annotations

import datetime as dt
from io import StringIO

import paramiko
import yaml
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

COMPOSE_PATH = "/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml"
TARGET_CONTEXT = "/opt/mycosoft/website"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    raw = run(ssh, f"cat {COMPOSE_PATH}")
    doc = yaml.safe_load(StringIO(raw)) or {}
    services = doc.get("services") or {}
    website = services.get("mycosoft-website")
    if not isinstance(website, dict):
        raise SystemExit("[ERROR] services.mycosoft-website not found")

    build = website.get("build")
    if not isinstance(build, dict):
        raise SystemExit("[ERROR] mycosoft-website.build missing or not a map")

    prev = build.get("context")
    build["context"] = TARGET_CONTEXT

    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{COMPOSE_PATH}.bak-{ts}"
    run(ssh, f"cp {COMPOSE_PATH} {backup}")

    new_raw = yaml.dump(doc, sort_keys=False)
    run(ssh, "cat > /tmp/docker-compose.always-on.yml << 'EOF'\n" + new_raw + "\nEOF")
    run(ssh, f"mv /tmp/docker-compose.always-on.yml {COMPOSE_PATH}")

    print("[OK] Updated build context")
    print(" - compose:", COMPOSE_PATH)
    print(" - previous context:", prev)
    print(" - new context:", TARGET_CONTEXT)
    print(" - backup:", backup)

    print("\n[rebuild+recreate] website")
    print(run(ssh, f"cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache"))
    print(run(ssh, f"cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website"))

    ssh.close()


if __name__ == "__main__":
    main()

