#!/usr/bin/env python3
"""Upload a local file to the sandbox VM via SFTP (Paramiko).

This avoids complex shell-quoting issues when we need to place scripts on the VM.

Usage:
  python scripts/vm_upload_file.py --local scripts/vm_payloads/setup_nas_website_assets.sh --remote /home/mycosoft/setup_nas_website_assets.sh --chmod 755
"""

from __future__ import annotations

import argparse
import os
import sys

import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--local", required=True, help="Local path (relative or absolute)")
    ap.add_argument("--remote", required=True, help="Remote absolute path on VM")
    ap.add_argument("--chmod", type=str, default="", help="Octal chmod (e.g. 755)")
    args = ap.parse_args()

    local_path = os.path.abspath(args.local)
    if not os.path.isfile(local_path):
        raise SystemExit(f"Local file not found: {local_path}")
    if not args.remote.startswith("/"):
        raise SystemExit("--remote must be an absolute path on the VM.")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    sftp = ssh.open_sftp()
    sftp.put(local_path, args.remote)

    if args.chmod:
        mode = int(args.chmod, 8)
        sftp.chmod(args.remote, mode)

    sftp.close()
    ssh.close()

    print(f"[OK] Uploaded {local_path} -> {args.remote}")
    if args.chmod:
        print(f"[OK] chmod {args.chmod} {args.remote}")


if __name__ == "__main__":
    main()

