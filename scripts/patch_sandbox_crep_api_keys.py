#!/usr/bin/env python3
"""
Merge CREP-related API keys into Sandbox VM website .env and recreate Next.js containers
so new env is loaded. Keys are read from a JSON file path (argv[1]) then deleted by caller.

Expected JSON keys: OPENAIP_API_KEY, SF_511_API_KEY, GLOBAL_FISHING_WATCH_TOKEN

Usage (from repo root, after writing a temp JSON file):
  python scripts/patch_sandbox_crep_api_keys.py C:\\path\\to\\keys.json

Uses .credentials.local for VM SSH (VM_PASSWORD / VM_SSH_PASSWORD).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

KEYS = ("OPENAIP_API_KEY", "SF_511_API_KEY", "GLOBAL_FISHING_WATCH_TOKEN")
VM_HOST = os.environ.get("SANDBOX_VM_HOST", "192.168.0.187")
VM_USER = os.environ.get("SANDBOX_VM_USER", os.environ.get("VM_SSH_USER", "mycosoft"))
REMOTE_PATHS = (
    "/opt/mycosoft/website/.env",
    "/opt/mycosoft/.env",
)


def load_credentials() -> None:
    mas = Path(__file__).resolve().parent.parent
    website = mas.parent / "WEBSITE" / "website"
    for base in (mas, website):
        for fname in (".credentials.local", ".env.local"):
            p = base / fname
            if not p.exists():
                continue
            for line in p.read_text().splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip("\"'").strip()


def quote_env_value(val: str) -> str:
    """Docker .env: quote if needed."""
    if not val:
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_.:/+-]+", val):
        return val
    esc = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def merge_env_file(content: str, updates: dict[str, str]) -> str:
    drop = set(updates.keys())
    lines_out: list[str] = []
    for line in content.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            key = s.split("=", 1)[0].strip()
            if key in drop:
                continue
        lines_out.append(line)
    for k in KEYS:
        if k in updates and updates[k]:
            lines_out.append(f"{k}={quote_env_value(updates[k])}")
    body = "\n".join(lines_out)
    if body and not body.endswith("\n"):
        body += "\n"
    return body


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python patch_sandbox_crep_api_keys.py <path-to-keys.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    updates = {k: str(data.get(k) or "").strip() for k in KEYS}
    missing = [k for k in KEYS if not updates[k]]
    if missing:
        print(f"ERROR: missing keys in JSON: {missing}", file=sys.stderr)
        return 1

    load_credentials()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        print("ERROR: VM_PASSWORD / VM_SSH_PASSWORD not set (.credentials.local).", file=sys.stderr)
        return 1

    try:
        import paramiko
    except ImportError:
        print("ERROR: pip install paramiko", file=sys.stderr)
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(VM_HOST, username=VM_USER, password=pw, timeout=45)
    except Exception as e:
        print(f"ERROR: SSH failed: {e}", file=sys.stderr)
        return 1

    try:
        sftp = client.open_sftp()
        for remote in REMOTE_PATHS:
            try:
                with sftp.file(remote, "r") as rf:
                    raw = rf.read().decode("utf-8", errors="replace")
            except FileNotFoundError:
                print(f"Skip (missing): {remote}")
                continue
            new_body = merge_env_file(raw, updates)
            with sftp.file(remote, "w") as wf:
                wf.write(new_body.encode("utf-8"))
            print(f"Updated {remote} ({len(new_body)} bytes)")
        sftp.close()

        # Recreate website containers so Docker injects new env (restart alone is not enough).
        cmds = [
            "cd /opt/mycosoft/website && docker compose -f docker-compose.production.yml -f docker-compose.production.blue-green.yml up -d --force-recreate website-blue website-green 2>&1",
            "cd /opt/mycosoft/website && docker compose -p mycosoft-production up -d --force-recreate mycosoft-website 2>&1",
        ]
        for cmd in cmds:
            stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            code = stdout.channel.recv_exit_status()
            if out.strip():
                print(out.strip()[:2000])
            if err.strip():
                print(err.strip()[:500], file=sys.stderr)
            if code == 0:
                print("Compose recreate command succeeded.")
                break
        else:
            print("WARN: No compose recreate returned 0; check services manually.", file=sys.stderr)

    finally:
        client.close()

    print("Done. Purge Cloudflare if changes do not appear on mycosoft.com.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
