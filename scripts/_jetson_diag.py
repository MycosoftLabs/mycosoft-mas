#!/usr/bin/env python3
"""Quick Jetson 123 diagnostics for OpenClaw reachability."""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("paramiko not installed")
    sys.exit(1)

HOST = "192.168.0.123"
USER = "jetson"
PORT = 18789

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
pw = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or ""
if not pw and creds.exists():
    for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() in ("JETSON_SSH_PASSWORD", "VM_PASSWORD", "VM_SSH_PASSWORD") and v.strip():
            pw = v.strip()
            break

if not pw:
    print("No password in .credentials.local or env")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=pw, timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    so = stdout.read().decode(errors="replace")
    se = stderr.read().decode(errors="replace")
    return so, se, stdout.channel.recv_exit_status()

print("=== ss -tlnp | grep 18789 ===")
o, e, _ = run("ss -tlnp 2>/dev/null | grep 18789 || echo '(none)'")
print(o or "(empty)")

print("\n=== curl 127.0.0.1:18789 from Jetson ===")
o, e, _ = run("curl -s -w '\\nHTTP_CODE:%{http_code}' http://127.0.0.1:18789/ 2>&1 || echo FAIL")
print(o or e or "(empty)")

print("\n=== journalctl --user -u openclaw-gateway -n 15 ===")
o, e, _ = run("journalctl --user -u openclaw-gateway -n 15 --no-pager 2>&1")
print(o or e or "(empty)")

ssh.close()
print("\nDone.")
