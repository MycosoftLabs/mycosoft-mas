"""One-shot: MAS VM 188 — listeners on 8001, curl health, journal tail."""
from __future__ import annotations

import os
import shlex
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

    def run(cmd: str) -> tuple[str, str]:
        _, o, e = c.exec_command(cmd)
        return o.read().decode(errors="replace"), e.read().decode(errors="replace")

    for label, cmd in [
        ("net", "hostname; ip -br a | head -20"),
        ("active", "systemctl is-active mas-orchestrator"),
        ("ss8001", "ss -tlnp 2>/dev/null | grep 8001 || echo 'ss_user: no 8001'"),
        (
            "ss8001_sudo",
            f"echo {shlex.quote(pw)} | sudo -S ss -tlnp 2>/dev/null | grep 8001 || echo 'ss_sudo: no 8001'",
        ),
        ("curl", "curl -sS -m 8 http://127.0.0.1:8001/health 2>&1; echo"),
        ("ps", "pgrep -af uvicorn | head -5 || true"),
        (
            "unit",
            "systemctl show mas-orchestrator -p MainPID -p ExecMainStatus -p ActiveState --no-pager",
        ),
    ]:
        out, err = run(cmd)
        print(f"=== {label} ===\n{out.strip()}")
        if err.strip():
            print(f"stderr: {err.strip()[:500]}")

    out, _ = run("journalctl -u mas-orchestrator -n 50 --no-pager 2>/dev/null")
    tail = out.strip()
    if len(tail) > 4000:
        tail = tail[-4000:]
    print("=== journal (last ~4k) ===\n", tail)

    c.close()


if __name__ == "__main__":
    main()
