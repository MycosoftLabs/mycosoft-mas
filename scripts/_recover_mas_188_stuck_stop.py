"""Force-recover mas-orchestrator on 188 when stuck in deactivating (stop-sigterm)."""
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


def sudo_pty(c: paramiko.SSHClient, pw: str, cmd: str) -> None:
    ch = c.get_transport().open_session()
    ch.get_pty()
    ch.exec_command(cmd)
    ch.send(pw + "\n")
    for _ in range(120):
        if ch.exit_status_ready():
            break
        time.sleep(0.25)
    ch.close()


def main() -> None:
    pw = load_creds()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=30)

    # SIGKILL cgroup so stop cannot hang forever
    sudo_pty(c, pw, "sudo -S systemctl kill -s SIGKILL mas-orchestrator")
    time.sleep(2)
    sudo_pty(c, pw, "sudo -S systemctl reset-failed mas-orchestrator")
    sudo_pty(c, pw, "sudo -S systemctl start mas-orchestrator")

    for attempt in range(36):
        i, o, e = c.exec_command("systemctl is-active mas-orchestrator")
        st = o.read().decode(errors="replace").strip()
        print(f"attempt {attempt + 1} is-active: {st!r}")
        if st == "active":
            break
        time.sleep(2)

    i, o, e = c.exec_command("ss -tlnp 2>/dev/null | grep 8001 || true")
    print("ss_8001:", o.read().decode(errors="replace").strip())
    i, o, e = c.exec_command("curl -sS -m 20 http://127.0.0.1:8001/health")
    body = o.read().decode(errors="replace")
    err = e.read().decode(errors="replace")
    print("health:", body[:1200])
    if err.strip():
        print("health_stderr:", err[:500])

    c.close()


if __name__ == "__main__":
    main()
