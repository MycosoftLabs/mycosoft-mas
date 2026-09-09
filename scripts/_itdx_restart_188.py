"""SFTP ITDX routers to MAS 188 and restart mas-orchestrator. No secrets printed."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "mycosoft_mas/core/routers/itdx_api.py",
    "mycosoft_mas/core/routers/itdx_public_sources.py",
    "tests/test_itdx_task8_api.py",
]


def load_creds() -> None:
    creds = ROOT / ".credentials.local"
    if not creds.exists():
        return
    for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect() -> paramiko.SSHClient:
    host = os.environ.get("MAS_VM_HOST") or os.environ.get("MAS_VM_IP") or "192.168.0.188"
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        username="mycosoft",
        password=password,
        timeout=25,
        allow_agent=True,
        look_for_keys=True,
    )
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 90, use_sudo: bool = False) -> str:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if use_sudo:
        cmd = f"sudo -S -p '' {cmd}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=use_sudo)
    if use_sudo:
        stdin.write(password + "\n")
        stdin.flush()
        stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if password:
        out = out.replace(password, "***")
        err = err.replace(password, "***")
    return (out + ("\n" + err if err.strip() else "")).replace("\u25cf", "*")


def main() -> int:
    load_creds()
    client = connect()
    remote_root = "/home/mycosoft/mycosoft/mas"
    try:
        sftp = client.open_sftp()
        for rel in FILES:
            local = ROOT / rel
            remote = f"{remote_root}/{rel}"
            sftp.put(str(local), remote)
            print("PUT", rel)
        sftp.close()
        print(run(client, "systemctl restart mas-orchestrator && echo RESTARTED", timeout=120, use_sudo=True))
        time.sleep(4)
        print(
            "HEALTH",
            run(
                client,
                "curl -sS -m 8 -o /tmp/itdx_h.txt -w '%{http_code}' http://127.0.0.1:8001/api/itdx/health; echo; "
                "head -c 240 /tmp/itdx_h.txt; echo; systemctl is-active mas-orchestrator",
                timeout=30,
            ),
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
