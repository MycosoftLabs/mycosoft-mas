"""Clean rebuild path for MAS orchestrator on 188: free 8001, pull main, venv sync, systemd restart, verify."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


def exec_plain(client: paramiko.SSHClient, cmd: str, timeout: float = 600) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command(cmd, timeout=int(timeout) + 60)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return stdout.channel.recv_exit_status(), out, err


def sudo_restart(client: paramiko.SSHClient, pw: str) -> None:
    ch = client.get_transport().open_session()
    ch.get_pty()
    ch.exec_command("sudo -S systemctl restart mas-orchestrator")
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
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=45)

    print("=== 1) Remove legacy Docker binding 8001 (idempotent) ===")
    code0, o0, e0 = exec_plain(
        c,
        "docker stop myca-orchestrator-new 2>/dev/null || true; "
        "docker rm -f myca-orchestrator-new 2>/dev/null || true",
        timeout=60,
    )
    print("exit", code0, (o0 + e0).strip()[-500:] or "(ok)")

    print("=== 2) git reset to origin/main + venv pip install -e . ===")
    pull_cmd = (
        "set -e; cd /home/mycosoft/mycosoft/mas && "
        "git fetch origin && git reset --hard origin/main && "
        "test -x ./venv/bin/pip && ./venv/bin/pip install -e . -q"
    )
    code1, o1, e1 = exec_plain(c, f"bash -lc {repr(pull_cmd)}", timeout=600)
    tail = (o1 + e1).strip()
    print("exit", code1, tail[-4000:] if tail else "(empty)")

    print("=== 3) systemctl restart mas-orchestrator ===")
    sudo_restart(c, pw)
    time.sleep(8)

    print("=== 4) ss :8001 + unit state ===")
    _, ss, _ = exec_plain(c, "ss -tlnp 2>/dev/null | grep 8001 || true", timeout=30)
    print("ss_8001:", ss.strip())
    _, act, _ = exec_plain(c, "systemctl is-active mas-orchestrator", timeout=30)
    print("mas-orchestrator:", act.strip())

    print("=== 5) GET /live (fast liveness) ===")
    _, live, le = exec_plain(c, "curl -sS -m 8 -w '\\nHTTP_CODE:%{http_code}' http://127.0.0.1:8001/live", timeout=20)
    print(live.strip()[-800:])
    if le.strip():
        print("live_stderr:", le.strip()[:400])

    print("=== 6) GET /health (may be slow; deep checks) ===")
    _, health, he = exec_plain(c, "curl -sS -m 60 http://127.0.0.1:8001/health", timeout=90)
    print(health.strip()[:1200])
    if he.strip():
        print("health_stderr:", he.strip()[:400])

    c.close()
    if code1 != 0:
        raise SystemExit(f"git/pip step failed with exit {code1}")
    if "active" not in act.strip().lower():
        raise SystemExit("mas-orchestrator not active")


if __name__ == "__main__":
    main()
