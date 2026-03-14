#!/usr/bin/env python3
"""Copy install script to Jetson and run it. Uses JETSON_SSH_PASSWORD from env or .credentials.local."""
from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path

import paramiko


def load_jetson_password() -> str:
    pw = os.environ.get("JETSON_SSH_PASSWORD", "")
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if not pw and creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "JETSON_SSH_PASSWORD" and v.strip():
                pw = v.strip()
                break
    return pw


def main() -> int:
    host = "192.168.0.123"
    user = "jetson"
    script_path = Path(__file__).resolve().parents[1] / "deploy" / "jetson" / "install_cursor_and_chromium.sh"

    if not script_path.exists():
        print(f"ERROR: Install script not found: {script_path}")
        return 1

    pw = load_jetson_password()
    if not pw:
        print("ERROR: Set JETSON_SSH_PASSWORD in env or add to .credentials.local")
        return 1

    print(f"Connecting to {user}@{host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=pw, timeout=30)
    except Exception as e:
        print(f"SSH connect failed: {e}")
        return 1

    try:
        # Upload script (normalize to LF to avoid $'\r': command not found on Linux)
        remote_path = f"/home/{user}/install_cursor_and_chromium.sh"
        content = script_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        sftp = ssh.open_sftp()
        sftp.putfo(BytesIO(content.encode("utf-8")), remote_path)
        sftp.close()
        print(f"Uploaded {script_path.name} -> {remote_path} (LF line endings)")

        # Run script (sudo -S reads password from stdin)
        _stdin, stdout, stderr = ssh.exec_command(
            f"chmod +x {remote_path} && echo '{pw}' | sudo -S bash {remote_path}",
            timeout=600,
        )
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        print(out)
        if err:
            print(err, file=sys.stderr)
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
