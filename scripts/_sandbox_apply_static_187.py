#!/usr/bin/env python3
r"""
Set sandbox primary NIC to static 192.168.0.187/24 (gateway 192.168.0.1).

Connects via SANDBOX_SSH_HOST or 192.168.0.248, then 192.168.0.187.
Aborts if ping to .187 succeeds before apply (possible IP conflict).
Uses sudo -S with VM password.
"""
from __future__ import annotations

import os
import socket
import sys
import time
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent
for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.strip().startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""

NETPLAN_SNIPPET = """network:
  version: 2
  ethernets:
    enp6s18:
      dhcp4: false
      addresses:
        - 192.168.0.187/24
      routes:
        - to: default
          via: 192.168.0.1
      nameservers:
        addresses: [192.168.0.1, 8.8.8.8]
"""

REMOTE_SCRIPT = f"""set -e
# If enp6s18 already has .187, skip ping (ping to self would false-trigger "conflict")
if ip -4 -o addr show dev enp6s18 2>/dev/null | grep -q '192.168.0.187/'; then
  echo "enp6s18 already has 192.168.0.187 — idempotent netplan refresh only"
else
  if ping -c 1 -W 2 192.168.0.187 >/dev/null 2>&1; then
    echo "ABORT: 192.168.0.187 responds to ping — possible IP conflict"
    exit 2
  fi
fi
cat > /etc/netplan/99-mycosoft-static.yaml <<'NETPLAN_EOF'
{NETPLAN_SNIPPET}NETPLAN_EOF
chmod 600 /etc/netplan/99-mycosoft-static.yaml
netplan generate
netplan apply
ip -4 -br addr show enp6s18 || true
echo OK
"""


def _connect(host: str) -> paramiko.SSHClient:
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(host, username="mycosoft", password=pw, timeout=20)
    return s


def main() -> int:
    if not pw:
        print("no VM password")
        return 1
    env_host = (os.environ.get("SANDBOX_SSH_HOST") or "").strip()
    hosts = [h for h in (env_host, "192.168.0.248", "192.168.0.187") if h]
    s: paramiko.SSHClient | None = None
    host_used = ""
    for h in hosts:
        try:
            s = _connect(h)
            host_used = h
            break
        except Exception as ex:
            print(f"{h}: {ex}")
    if not s:
        print("Could not SSH to sandbox")
        return 1
    print(f"Connected {host_used}")
    stdin, stdout, stderr = s.exec_command("sudo -S bash -s", get_pty=True)
    ch = stdout.channel
    ch.settimeout(2.0)
    stdin.write(pw + "\n")
    stdin.flush()
    time.sleep(0.25)
    stdin.write(REMOTE_SCRIPT)
    stdin.flush()
    stdin.channel.shutdown_write()
    out_parts: list[str] = []
    err_parts: list[str] = []
    deadline = time.time() + 180.0
    code = -1
    while time.time() < deadline:
        try:
            if ch.recv_ready():
                out_parts.append(ch.recv(65536).decode(errors="replace"))
            if ch.recv_stderr_ready():
                err_parts.append(ch.recv_stderr(65536).decode(errors="replace"))
        except socket.timeout:
            pass
        if ch.closed or ch.exit_status_ready():
            while ch.recv_ready():
                out_parts.append(ch.recv(65536).decode(errors="replace"))
            while ch.recv_stderr_ready():
                err_parts.append(ch.recv_stderr(65536).decode(errors="replace"))
            break
        if not ch.closed and not ch.exit_status_ready():
            time.sleep(0.1)
    out = "".join(out_parts)
    err = "".join(err_parts)
    try:
        code = ch.recv_exit_status() if ch.exit_status_ready() else -1
    except Exception:
        code = -1
    if code == -1 and "OK" in out:
        code = 0
    if out.strip():
        print(out)
    if err.strip():
        print("stderr:", err)
    s.close()
    print("exit:", code)
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
