"""One-shot: remove Docker orchestrator binding 8001, restart systemd mas-orchestrator."""
from __future__ import annotations

import os
import time
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent


def load_creds() -> str:
    p = REPO / ".credentials.local"
    for line in p.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        raise SystemExit("No VM_PASSWORD / VM_SSH_PASSWORD")
    return pw


def main() -> None:
    pw = load_creds()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=30)

    for cmd in (
        "docker stop myca-orchestrator-new 2>/dev/null; true",
        "docker rm myca-orchestrator-new 2>/dev/null; true",
    ):
        i, o, e = c.exec_command(cmd)
        i.close()
        _ = o.read()
        _ = e.read()

    ch = c.get_transport().open_session()
    ch.get_pty()
    ch.exec_command("sudo -S systemctl restart mas-orchestrator")
    ch.send(pw + "\n")
    for _ in range(60):
        if ch.exit_status_ready():
            break
        time.sleep(0.25)
    ch.close()

    i, o, e = c.exec_command("ss -tlnp 2>/dev/null | grep 8001 || true")
    print("ss_8001:", o.read().decode(errors="replace").strip())
    i, o, e = c.exec_command("systemctl is-active mas-orchestrator")
    print("mas-orchestrator:", o.read().decode(errors="replace").strip())
    i, o, e = c.exec_command("curl -sS -m 15 http://127.0.0.1:8001/health")
    print("health_body:", o.read().decode(errors="replace")[:800])
    err = e.read().decode(errors="replace")
    if err.strip():
        print("health_err:", err[:500])
    c.close()


if __name__ == "__main__":
    main()
