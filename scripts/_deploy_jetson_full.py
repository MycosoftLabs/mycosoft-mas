#!/usr/bin/env python3
"""
Full Jetson 123 deploy: Cursor+Chromium, Node.js, OpenClaw, optional gateway.
Uses JETSON_SSH_PASSWORD or VM_PASSWORD from env or .credentials.local.
"""
from __future__ import annotations

import os
import sys
from io import BytesIO, TextIOWrapper
from pathlib import Path

import paramiko

# Windows console may not support UTF-8; wrap stdout/stderr to avoid UnicodeEncodeError on systemd output (e.g. ●)
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

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


def upload_and_run(ssh: paramiko.SSHClient, script_path: Path, run_cmd: str, pw: str, timeout: int = 600) -> int:
    """Upload script and run via sudo bash."""
    content = script_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    remote = f"/home/{USER}/{script_path.name}"
    sftp = ssh.open_sftp()
    sftp.putfo(BytesIO(content.encode("utf-8")), remote)
    sftp.close()
    full_cmd = f"chmod +x {remote} && echo '{pw}' | sudo -S bash {remote}"
    if run_cmd:
        full_cmd = run_cmd
    _stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(out)
    if err:
        print(err, file=sys.stderr)
    return code


def main() -> int:
    pw = load_password()
    if not pw:
        print("ERROR: Set JETSON_SSH_PASSWORD or VM_PASSWORD in env or .credentials.local")
        return 1

    mas_root = Path(__file__).resolve().parents[1]
    deploy_dir = mas_root / "deploy" / "jetson"

    print(f"Connecting to {USER}@{HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=pw, timeout=30)
    except Exception as e:
        print(f"SSH connect failed: {e}")
        return 1

    try:
        # 1. Install Node.js 22 if not present (required for OpenClaw)
        print("\n=== Step 1: Node.js 22 ===")
        _stdin, stdout, stderr = ssh.exec_command("node -v 2>/dev/null || true", timeout=10)
        node_ver = stdout.read().decode().strip()
        if not node_ver or "v2" not in node_ver:
            node_sh = deploy_dir / "install_node22.sh"
            if node_sh.exists():
                code = upload_and_run(ssh, node_sh, "", pw, timeout=180)
                if code != 0:
                    print("WARNING: Node install may have failed; continuing...")
            else:
                print("install_node22.sh not found, skipping Node install")
        else:
            print(f"Node already present: {node_ver}")

        # 2. Install OpenClaw
        print("\n=== Step 2: OpenClaw ===")
        openclaw_sh = deploy_dir / "install_openclaw.sh"
        if openclaw_sh.exists():
            content = openclaw_sh.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
            remote = f"/home/{USER}/install_openclaw.sh"
            sftp = ssh.open_sftp()
            sftp.putfo(BytesIO(content.encode("utf-8")), remote)
            sftp.close()
            # Run as jetson user (no sudo for npm install -g)
            _stdin, stdout, stderr = ssh.exec_command(
                f"chmod +x {remote} && bash {remote}",
                timeout=300,
            )
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            print(out)
            if err:
                print(err, file=sys.stderr)
            if stdout.channel.recv_exit_status() != 0:
                print("WARNING: OpenClaw install had issues")

            # Fix OpenClaw service: systemd has minimal PATH; use absolute path to openclaw
            print("Fixing OpenClaw service (ensure ExecStart uses absolute path)...")
            fix_cmd = """
            NPM_BIN=$(npm bin -g 2>/dev/null)
            OC_PATH=""
            if [ -n "$NPM_BIN" ] && [ -x "$NPM_BIN/openclaw" ]; then
              OC_PATH="$NPM_BIN/openclaw"
            else
              OC_PATH=$(command -v openclaw 2>/dev/null)
            fi
            if [ -n "$OC_PATH" ]; then
              SVC="$HOME/.config/systemd/user/openclaw-gateway.service"
              if [ -f "$SVC" ]; then
                # Update ExecStart to use absolute path; keep Environment=PATH for deps
                sed -i "s|^ExecStart=.*|ExecStart=$OC_PATH gateway --port 18789 --host 0.0.0.0|" "$SVC"
                echo "Updated ExecStart to: $OC_PATH"
              fi
            else
              echo "WARNING: Could not find openclaw binary"
            fi
            """
            _stdin, stdout, stderr = ssh.exec_command(f"bash -c {repr(fix_cmd)}", timeout=15)
            print(stdout.read().decode("utf-8", errors="replace"))

            # Enable and start OpenClaw user service
            print("Enabling OpenClaw user service...")
            _stdin, stdout, stderr = ssh.exec_command(
                "systemctl --user daemon-reload 2>/dev/null; "
                "systemctl --user enable openclaw-gateway 2>/dev/null; "
                "systemctl --user start openclaw-gateway 2>/dev/null; "
                "systemctl --user status openclaw-gateway --no-pager 2>/dev/null || true",
                timeout=15,
            )
            print(stdout.read().decode("utf-8", errors="replace"))
        else:
            print("install_openclaw.sh not found, skipping")

        # 3. Cursor + Chromium
        print("\n=== Step 3: Cursor + Chromium ===")
        cursor_sh = deploy_dir / "install_cursor_and_chromium.sh"
        if cursor_sh.exists():
            content = cursor_sh.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
            remote = f"/home/{USER}/install_cursor_and_chromium.sh"
            sftp = ssh.open_sftp()
            sftp.putfo(BytesIO(content.encode("utf-8")), remote)
            sftp.close()
            _stdin, stdout, stderr = ssh.exec_command(
                f"chmod +x {remote} && echo '{pw}' | sudo -S bash {remote}",
                timeout=600,
            )
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            print(out)
            if err:
                print(err, file=sys.stderr)
        else:
            print("install_cursor_and_chromium.sh not found, skipping")

        # 4. Summary
        print("\n=== Deploy complete ===")
        print(f"OpenClaw Control UI: http://{HOST}:18789/")
        print("Device Manager -> On-Site AI -> Open OpenClaw")
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
