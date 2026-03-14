#!/usr/bin/env python3
"""Run Jetson browser fix script over SSH. Fixes Chromium/Firefox not opening (Snap 2.70 issue).
Uses JETSON_SSH_PASSWORD or VM_PASSWORD from env or .credentials.local.

  --flatpak-only   Skip snap revert/downgrade; install Flatpak Chromium + Epiphany directly.
                   Use when snap Chromium still fails after downgrade (spinner, no window)."""
from __future__ import annotations

import argparse
import os
import sys
from io import BytesIO
from pathlib import Path

import paramiko


def load_jetson_password() -> str:
    pw = (
        os.environ.get("JETSON_SSH_PASSWORD", "")
        or os.environ.get("VM_PASSWORD", "")
        or os.environ.get("VM_SSH_PASSWORD", "")
    )
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if not pw and creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in ("JETSON_SSH_PASSWORD", "VM_PASSWORD", "VM_SSH_PASSWORD") and v:
                pw = v
                break
    return pw


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Jetson browser fix over SSH")
    ap.add_argument(
        "--flatpak-only",
        action="store_true",
        help="Skip snap steps; install Flatpak Chromium + Epiphany only (use when snap Chromium still broken)",
    )
    args = ap.parse_args()

    host = "192.168.0.123"
    user = "jetson"
    script_path = Path(__file__).resolve().parents[1] / "deploy" / "jetson" / "fix_jetson_browsers.sh"

    if not script_path.exists():
        print(f"ERROR: Fix script not found: {script_path}")
        return 1

    pw = load_jetson_password()
    if not pw:
        print("ERROR: Set JETSON_SSH_PASSWORD or VM_PASSWORD in env or add to .credentials.local")
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
        remote_path = f"/home/{user}/fix_jetson_browsers.sh"
        content = script_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        sftp = ssh.open_sftp()
        sftp.putfo(BytesIO(content.encode("utf-8")), remote_path)
        sftp.close()
        print(f"Uploaded fix_jetson_browsers.sh -> {remote_path}")

        env_prefix = "env FLATPAK_ONLY=1 " if args.flatpak_only else ""
        if args.flatpak_only:
            print("Running Flatpak-only fix (skipping snap steps)...")
        else:
            print("Running browser fix (may take several minutes for Flatpak)...")
        _stdin, stdout, stderr = ssh.exec_command(
            f"chmod +x {remote_path} && echo '{pw}' | sudo -S {env_prefix}bash {remote_path}",
            timeout=900,
        )
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        print(out)
        if err:
            print(err, file=sys.stderr)
        print("\nIf Flatpak Chromium was installed: try 'flatpak run org.chromium.Chromium' or the desktop icon.")
        print("A reboot may help: ssh jetson@192.168.0.123 'echo <password> | sudo -S reboot'")
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
