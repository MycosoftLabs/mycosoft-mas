"""One-shot: SSH 188, check mas-orchestrator, curl /live, journal tail."""
from __future__ import annotations

import os
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    for line in (REPO / ".credentials.local").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        raise SystemExit("no creds")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=45)

    def run(cmd: str, t: int = 120) -> tuple[str, str, int]:
        _, o, e = c.exec_command(cmd, timeout=t)
        out = o.read().decode("utf-8", "replace")
        err = e.read().decode("utf-8", "replace")
        return out, err, o.channel.recv_exit_status()

    o, _, _ = run("systemctl is-active mas-orchestrator; ss -tlnp | grep 8001 || true")
    print("=== unit + ss ===\n", o.strip())

    for i in range(6):
        o2, _, _ = run(
            "curl -sS -m 8 -w '\\nCODE:%{http_code}' http://127.0.0.1:8001/live 2>&1"
        )
        print(f"=== try {i + 1} /live ===\n", o2.strip()[-600:])
        if "CODE:200" in o2:
            break

    o3, _, _ = run("journalctl -u mas-orchestrator -n 50 --no-pager")
    print("=== journal tail ===\n", o3[-2800:])
    c.close()


if __name__ == "__main__":
    main()
