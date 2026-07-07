#!/usr/bin/env python3
"""Deploy Psathyrella bearer fix to MAS VM 188 (fetch branch + restart)."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

COMMIT = "7536f553e"
BRANCH = "chore/license-notice-readme-sweep-jun25-2026"
HOST = "192.168.0.188"
USER = "mycosoft"

REPO_CANDIDATES = [
    "/home/mycosoft/mycosoft/mas",
    "/home/mycosoft/mycosoft-mas",
    "/opt/mycosoft/mas",
]


def load_credentials() -> None:
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if creds.exists():
        for line in creds.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def run(ssh: paramiko.SSHClient, cmd: str, sudo: bool = False) -> tuple[int, str, str]:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    if sudo:
        cmd = f"echo {pw!r} | sudo -S bash -lc {cmd!r}"
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def main() -> int:
    load_credentials()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    if not pw:
        print("Missing VM_PASSWORD in .credentials.local", file=sys.stderr)
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=pw, timeout=30)

    repo = ""
    for candidate in REPO_CANDIDATES:
        code, out, _ = run(ssh, f"test -d {candidate}/.git && echo {candidate}")
        if code == 0 and out.strip():
            repo = out.strip().splitlines()[-1]
            break
    if not repo:
        print("Could not locate MAS git repo on VM", file=sys.stderr)
        ssh.close()
        return 1
    print(f"Repo: {repo}")

    deploy_cmd = f"""
set -e
cd {repo}
git fetch origin {BRANCH}
git reset --hard {COMMIT}
git log -1 --oneline
"""
    code, out, err = run(ssh, deploy_cmd)
    print(out)
    if code != 0:
        print(err, file=sys.stderr)
        ssh.close()
        return code

    # Prefer systemd; fall back to docker container restart
    code, svc_out, _ = run(ssh, "systemctl is-active mas-orchestrator 2>/dev/null || echo inactive")
    if "active" in svc_out:
        print("Restarting mas-orchestrator (systemd)...")
        code, out, err = run(ssh, "systemctl restart mas-orchestrator", sudo=True)
    else:
        print("Restarting myca-orchestrator-new (docker)...")
        code, out, err = run(
            ssh,
            "docker restart myca-orchestrator-new 2>/dev/null || "
            "docker restart mycosoft-mas-mas-orchestrator-1 2>/dev/null || "
            "docker ps --format '{{.Names}}' | grep -i orchestrator | head -1 | xargs -r docker restart",
            sudo=True,
        )
    print(out or err)
    if code != 0:
        ssh.close()
        return code

    print("Waiting for health...")
    time.sleep(12)
    ssh.close()

    import urllib.request

    for url in ("http://192.168.0.188:8001/health",):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                print(f"{url} -> {resp.status} {resp.read()[:200].decode()}")
        except Exception as exc:
            print(f"{url} FAILED: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
