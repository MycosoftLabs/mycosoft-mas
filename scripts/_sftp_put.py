#!/usr/bin/env python3
"""Upload one file to a VM using credentials from .credentials.local."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import paramiko


def load_password() -> str:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if creds.exists():
        for raw in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key in {"VM_PASSWORD", "VM_SSH_PASSWORD"} and value:
                pw = value
                break
    return pw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--local", required=True)
    parser.add_argument("--remote", required=True)
    args = parser.parse_args()

    local_path = Path(args.local).expanduser().resolve()
    if not local_path.exists():
        raise SystemExit(f"Local file not found: {local_path}")
    if not args.remote.startswith("/"):
        raise SystemExit("--remote must be an absolute path")

    password = load_password()
    if not password:
        raise SystemExit("Missing VM_PASSWORD/VM_SSH_PASSWORD")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.host, username="mycosoft", password=password, timeout=30)
    try:
        sftp = ssh.open_sftp()
        try:
            sftp.put(str(local_path), args.remote)
        finally:
            sftp.close()
    finally:
        ssh.close()

    print(f"Uploaded {local_path} -> {args.remote}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

