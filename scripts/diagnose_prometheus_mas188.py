"""SSH to MAS VM 188: diagnose Prometheus (Docker, localhost health, port listen).

Reads VM_PASSWORD or VM_SSH_PASSWORD from repo .credentials.local.

Run from a shell that can read .credentials.local (external PowerShell if Cursor
sandbox hides gitignored files):

  cd mycosoft-mas
  python scripts/diagnose_prometheus_mas188.py

Optional remediation (requires sudo on VM): open LAN to 9090 — see
docs/PROMETHEUS_MAS_VM188_RUNBOOK_MAY03_2026.md
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[1]
CRED = REPO / ".credentials.local"
MAS_IP = "192.168.0.188"
USER = "mycosoft"


def load_vm_password() -> str:
    for env_key in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
        v = os.environ.get(env_key, "").strip()
        if v:
            return v
    cred_path = os.environ.get("MYCO_SOFT_CREDENTIALS_FILE", "").strip()
    paths = [Path(cred_path).expanduser() if cred_path else None, CRED]
    for p in paths:
        if not p or not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            for key in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                m = re.match(rf"^\s*{key}\s*=\s*(.+)\s*$", line)
                if m:
                    return m.group(1).strip().strip('"').strip("'")
    raise SystemExit(
        "No VM password: set VM_PASSWORD or MYCO_SOFT_CREDENTIALS_FILE, or ensure "
        f"{CRED} exists on disk (Cursor sandbox may hide gitignored files)."
    )


def main() -> None:
    pw = load_vm_password()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(MAS_IP, username=USER, password=pw, timeout=25)

    def run(cmd: str) -> tuple[int, str, str]:
        _, out, err = c.exec_command(cmd, timeout=120)
        o = out.read().decode("utf-8", errors="replace")
        e = err.read().decode("utf-8", errors="replace")
        code = out.channel.recv_exit_status()
        return code, o, e

    checks = [
        ("docker_prom", "docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -iE 'prometheus|prom' || true"),
        ("docker_head", "docker ps -a --format '{{.Names}}\t{{.Status}}' | head -30"),
        ("curl_local", "curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:9090/-/healthy || echo FAIL"),
        ("ss_9090", "ss -tlnp 2>/dev/null | grep 9090 || true"),
    ]
    for label, cmd in checks:
        code, o, e = run(cmd)
        print(f"=== {label} exit={code} ===")
        print(o.rstrip())
        if e.strip():
            print("stderr:", e.strip()[:400])
    c.close()


if __name__ == "__main__":
    main()
