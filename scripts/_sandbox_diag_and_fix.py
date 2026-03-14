#!/usr/bin/env python3
"""Diagnose and fix sandbox tunnel/deploy issues on VM 187."""
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


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str]:
    _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace").strip()
    return code, out


def ensure_dns_and_tunnel(ssh: paramiko.SSHClient, pw: str) -> None:
    # Force reliable upstream DNS so cloudflared does not query dead ::1 resolver.
    dns_fix = (
        "sudo -S bash -lc \"cat > /etc/systemd/resolved.conf <<'EOF'\n"
        "[Resolve]\n"
        "DNS=1.1.1.1 1.0.0.1 8.8.8.8\n"
        "FallbackDNS=9.9.9.9 8.8.4.4\n"
        "DNSStubListener=yes\n"
        "EOF\""
    )
    stdin, stdout, stderr = ssh.exec_command(dns_fix, get_pty=True, timeout=120)
    stdin.write(pw + "\n")
    stdin.flush()
    _ = stdout.channel.recv_exit_status()
    _ = (stdout.read() + stderr.read()).decode("utf-8", errors="replace")

    restart_cmds = [
        "sudo -S systemctl restart systemd-resolved",
        "sudo -S ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf",
        "sudo -S systemctl restart cloudflared",
        "systemctl is-active cloudflared",
        "resolvectl status | sed -n '1,80p'",
        "journalctl -u cloudflared -n 30 --no-pager",
    ]
    for c in restart_cmds:
        stdin, stdout, stderr = ssh.exec_command(c, get_pty=True, timeout=120)
        stdin.write(pw + "\n")
        stdin.flush()
        code = stdout.channel.recv_exit_status()
        out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace").strip()
        print(f"\n### {c} (exit={code})")
        print(out[:6000] or "(no output)")


def main() -> int:
    pw = load_password()
    if not pw:
        print("ERROR: Missing VM password in env/.credentials.local")
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.187", username="mycosoft", password=pw, timeout=20)

    cmds = [
        "hostname",
        "uptime",
        "systemctl cat cloudflared",
        "ls -l /usr/bin/cloudflared /usr/local/bin/cloudflared 2>/dev/null || true",
        "journalctl -u cloudflared -n 80 --no-pager",
        "docker ps --format 'table {{.Names}}\\t{{.Status}}'",
        "ls -la /home/mycosoft/mycosoft",
        "ls -la /opt/mycosoft 2>/dev/null || true",
    ]
    for c in cmds:
        code, out = run(ssh, c)
        print(f"\n### {c} (exit={code})")
        print(out[:6000] or "(no output)")

    ensure_dns_and_tunnel(ssh, pw)

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
