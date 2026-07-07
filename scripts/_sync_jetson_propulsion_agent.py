#!/usr/bin/env python3
"""Push tracked jetson_agent.py to Jetson and restart psathyrella-agent user service."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_LOCAL = REPO_ROOT / "devices" / "psathyrella-jetson" / "jetson_agent.py"
AGENT_REMOTE = "/home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py"
HOST = os.getenv("JETSON_IP", "192.168.0.123")
USER = os.getenv("JETSON_SSH_USER", "jetson")


def load_credentials() -> str:
    creds = REPO_ROOT / ".credentials.local"
    if creds.exists():
        for line in creds.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    password = os.getenv("JETSON_SSH_PASSWORD") or os.getenv("VM_PASSWORD") or os.getenv("VM_SSH_PASSWORD")
    if not password:
        print("Missing JETSON_SSH_PASSWORD / VM_PASSWORD", file=sys.stderr)
        sys.exit(1)
    return password


def main() -> int:
    if not AGENT_LOCAL.is_file():
        print(f"Missing {AGENT_LOCAL}", file=sys.stderr)
        return 1
    password = load_credentials()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=password, timeout=30)
    sftp = ssh.open_sftp()
    backup = AGENT_REMOTE + ".bak-cursor-sync"
    try:
        sftp.stat(AGENT_REMOTE)
        ssh.exec_command(f"cp {AGENT_REMOTE} {backup}")
    except OSError:
        pass
    print(f"Uploading {AGENT_LOCAL.name} -> {AGENT_REMOTE}")
    sftp.put(str(AGENT_LOCAL), AGENT_REMOTE)
    sftp.close()
    _, stdout, stderr = ssh.exec_command("systemctl --user restart psathyrella-agent && sleep 2 && curl -s http://127.0.0.1:8788/health")
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out.strip() or err.strip())
    ssh.close()
    return 0 if "ok" in out.lower() else 1


if __name__ == "__main__":
    raise SystemExit(main())
