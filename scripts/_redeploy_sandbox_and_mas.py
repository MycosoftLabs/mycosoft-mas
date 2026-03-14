#!/usr/bin/env python3
"""Clean redeploy sandbox website (187) and MAS (188)."""
from __future__ import annotations

import os
from pathlib import Path

import paramiko


def load_password() -> str:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in {"VM_PASSWORD", "VM_SSH_PASSWORD"} and v.strip():
                pw = v.strip()
                break
    return pw


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 900) -> tuple[int, str]:
    _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace").strip()
    return code, out


def run_steps(host: str, pw: str, steps: list[tuple[str, int]]) -> bool:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username="mycosoft", password=pw, timeout=25)
    ok = True
    try:
        for cmd, timeout in steps:
            code, out = run(ssh, cmd, timeout=timeout)
            print(f"\n[{host}] $ {cmd}\nexit={code}", flush=True)
            if out:
                print(out[:8000], flush=True)
            if code != 0:
                ok = False
                print(f"[{host}] step failed", flush=True)
                break
    finally:
        ssh.close()
    return ok


def main() -> int:
    pw = load_password()
    if not pw:
        print("ERROR: missing VM password")
        return 1

    sandbox_steps = [
        ("hostname && uptime", 60),
        ("cd /home/mycosoft/mycosoft/website && git fetch origin && git reset --hard origin/main && git log -1 --oneline", 180),
        ("docker stop mycosoft-website || true", 60),
        ("docker rm mycosoft-website || true", 60),
        ("docker builder prune -af || true", 300),
        ("cd /home/mycosoft/mycosoft/website && docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .", 2400),
        (
            "docker run -d --name mycosoft-website -p 3000:3000 "
            "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
            "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest",
            120,
        ),
        ("sleep 10; docker ps --filter name=mycosoft-website --format '{{.Names}} {{.Status}}'", 60),
        ("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/", 60),
        ("systemctl is-active cloudflared && journalctl -u cloudflared -n 15 --no-pager", 60),
    ]
    print("=== Redeploy Sandbox 187 ===", flush=True)
    if not run_steps("192.168.0.187", pw, sandbox_steps):
        return 1

    mas_steps = [
        ("hostname && uptime", 60),
        ("cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main && git log -1 --oneline", 180),
        ("docker restart myca-orchestrator-new || true", 120),
        ("sleep 8; curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/health", 60),
    ]
    print("\n=== Redeploy MAS 188 ===", flush=True)
    if not run_steps("192.168.0.188", pw, mas_steps):
        return 1

    print("\nRedeploy complete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
