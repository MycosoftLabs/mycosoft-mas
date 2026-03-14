#!/usr/bin/env python3
"""Fix OpenClaw systemd service on Jetson 123 - resolve absolute path and restart."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

HOST = "192.168.0.123"
USER = "jetson"


def load_password() -> str:
    pw = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if not pw and creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ("JETSON_SSH_PASSWORD", "VM_PASSWORD", "VM_SSH_PASSWORD") and v.strip():
                pw = v.strip()
                break
    return pw


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 15) -> tuple[str, str, int]:
    _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return out, err, code


def safe_print(s: str) -> None:
    """Print with ASCII fallback for Windows console."""
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))


def main() -> int:
    pw = load_password()
    if not pw:
        print("ERROR: Set JETSON_SSH_PASSWORD or VM_PASSWORD")
        return 1

    print(f"Connecting to {USER}@{HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=pw, timeout=30)
    except Exception as e:
        print(f"SSH failed: {e}")
        return 1

    try:
        # 1. Diagnose: find openclaw and show current service
        print("\n--- Diagnosing ---")
        out, _, _ = run(ssh, "bash -l -c 'which openclaw 2>/dev/null' || true; cat ~/.config/systemd/user/openclaw-gateway.service 2>/dev/null")
        safe_print(out)

        # 2. Find openclaw path (login shell has npm global bin in PATH)
        print("\n--- Finding openclaw ---")
        out, _, _ = run(ssh, "bash -l -c 'which openclaw 2>/dev/null'")
        lines = [l.strip() for l in out.strip().splitlines() if l.strip() and l.strip().startswith("/")]
        oc_path = lines[-1] if lines else ""
        if not oc_path:
            # Try explicit paths and find
            out, _, _ = run(ssh, "find /usr/local /home/jetson/.local /home/jetson/.nvm -name openclaw -type f 2>/dev/null | head -5")
            for line in out.strip().splitlines():
                line = line.strip()
                if line and "openclaw" in line:
                    oc_path = line
                    break
        if not oc_path or "openclaw" not in oc_path:
            oc_path = "/usr/bin/npx openclaw"
            print(f"Using npx fallback: {oc_path}")
        else:
            print(f"Found: {oc_path}")

        # 3. Fix service file
        svc_path = "/home/jetson/.config/systemd/user/openclaw-gateway.service"
        run(ssh, f"sed -i.bak 's|^ExecStart=.*|ExecStart={oc_path} gateway --port 18789 --host 0.0.0.0|' {svc_path}")
        out, _, _ = run(ssh, f"cat {svc_path}")
        safe_print("\n--- Service file after fix ---\n" + out)

        # 3. Reload and restart
        print("\n--- Restarting OpenClaw ---")
        out, _, _ = run(ssh, "systemctl --user daemon-reload; systemctl --user restart openclaw-gateway; sleep 2; systemctl --user status openclaw-gateway --no-pager")
        safe_print(out)

        # 4. Verify HTTP
        print("\n--- Verifying HTTP ---")
        out, _, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/ 2>/dev/null || echo 'fail'")
        print(f"HTTP check: {out.strip()}")

        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
