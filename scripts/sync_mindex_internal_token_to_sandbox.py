#!/usr/bin/env python3
"""
Copy MINDEX internal token from VM 189 (mindex-api container env) into Sandbox 187
website .env as MINDEX_INTERNAL_TOKEN (single value = first of MINDEX_INTERNAL_TOKENS).

Optional: --dev-local copies the same value into a local file (default:
WEBSITE/website/.env.local relative to the repo tree) for `npm run dev:next-only`.

Does not print secret values. Uses .credentials.local for SSH.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MINDEX_HOST = os.environ.get("MINDEX_VM_IP", "192.168.0.189")
SANDBOX_HOST = os.environ.get("SANDBOX_VM_IP", "192.168.0.187")
VM_USER = os.environ.get("VM_SSH_USER", "mycosoft")
REMOTE_ENVS = (
    "/opt/mycosoft/website/.env",
    "/opt/mycosoft/.env",
)


def load_credentials() -> None:
    mas = Path(__file__).resolve().parent.parent
    for base in (mas, mas.parent / "WEBSITE" / "website"):
        p = base / ".credentials.local"
        if not p.is_file():
            continue
        for line in p.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip().strip("\"'").strip()


def parse_first_internal_token(env_lines: str) -> str | None:
    token_single = None
    tokens_plural = None
    for line in env_lines.splitlines():
        if line.startswith("MINDEX_INTERNAL_TOKEN="):
            token_single = line.split("=", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("MINDEX_INTERNAL_TOKENS="):
            raw = line.split("=", 1)[1].strip()
            if raw.startswith("["):
                try:
                    arr = json.loads(raw)
                    if isinstance(arr, list) and arr:
                        tokens_plural = str(arr[0]).strip()
                except json.JSONDecodeError:
                    tokens_plural = raw.split(",")[0].strip().strip('"').strip("'")
            else:
                tokens_plural = raw.split(",")[0].strip().strip('"').strip("'")
    return (token_single or tokens_plural or "").strip() or None


def merge_env(content: str, key: str, value: str) -> str:
    lines_out: list[str] = []
    drop = {key}
    for line in content.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in drop:
                continue
        lines_out.append(line)
    esc = value.replace("\\", "\\\\").replace('"', '\\"')
    quoted = f'"{esc}"' if re.search(r'[\s#]', value) else value
    lines_out.append(f"{key}={quoted}")
    body = "\n".join(lines_out)
    if body and not body.endswith("\n"):
        body += "\n"
    return body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dev-local",
        action="store_true",
        help="Also merge MINDEX_INTERNAL_TOKEN into local website .env.local (Next dev).",
    )
    ap.add_argument(
        "--dev-local-path",
        type=Path,
        default=None,
        help="Path to .env.local (default: ../../WEBSITE/website/.env.local from MAS repo).",
    )
    ap.add_argument(
        "--skip-sandbox",
        action="store_true",
        help="Do not update Sandbox 187; only --dev-local or fetch token for inspection.",
    )
    args = ap.parse_args()

    load_credentials()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        print("ERROR: VM_PASSWORD not set", file=sys.stderr)
        return 1
    try:
        import paramiko
    except ImportError:
        print("ERROR: pip install paramiko", file=sys.stderr)
        return 1

    c189 = paramiko.SSHClient()
    c189.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c189.connect(MINDEX_HOST, username=VM_USER, password=pw, timeout=45)
    try:
        _, stdout, _ = c189.exec_command(
            "docker inspect mindex-api --format '{{range .Config.Env}}{{println .}}{{end}}'"
        )
        env_blob = stdout.read().decode("utf-8", errors="replace")
    finally:
        c189.close()

    token = parse_first_internal_token(env_blob)
    if not token:
        print("ERROR: could not resolve MINDEX internal token from mindex-api", file=sys.stderr)
        return 1

    did_local = False
    if args.dev_local or args.dev_local_path is not None:
        # mycosoft-mas repo root -> CODE is parents[2] (…/CODE/MAS/mycosoft-mas)
        mas_repo = Path(__file__).resolve().parent.parent
        local_env = args.dev_local_path
        if local_env is None:
            code_root = mas_repo.parent.parent
            local_env = code_root / "WEBSITE" / "website" / ".env.local"
        else:
            local_env = local_env.resolve()
        if not local_env.parent.is_dir():
            print(f"ERROR: parent missing for {local_env}", file=sys.stderr)
            return 1
        old = local_env.read_text(encoding="utf-8", errors="replace") if local_env.is_file() else ""
        if re.search(r"^MINDEX_INTERNAL_TOKEN=", old, re.MULTILINE):
            print(f"OK: {local_env} already has MINDEX_INTERNAL_TOKEN (unchanged)")
        else:
            new_body = merge_env(old, "MINDEX_INTERNAL_TOKEN", token)
            local_env.write_text(new_body, encoding="utf-8")
            print(f"OK: wrote MINDEX_INTERNAL_TOKEN to {local_env} ({len(new_body)} bytes)")
        did_local = True

    if args.skip_sandbox:
        if not did_local:
            print("ERROR: --skip-sandbox with no --dev-local: nothing to update", file=sys.stderr)
            return 1
        return 0

    c187 = paramiko.SSHClient()
    c187.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c187.connect(SANDBOX_HOST, username=VM_USER, password=pw, timeout=45)
    try:
        sftp = c187.open_sftp()
        for remote in REMOTE_ENVS:
            try:
                with sftp.file(remote, "r") as rf:
                    raw = rf.read().decode("utf-8", errors="replace")
            except FileNotFoundError:
                print(f"Skip (missing): {remote}")
                continue
            if re.search(r"^MINDEX_INTERNAL_TOKEN=", raw, re.MULTILINE):
                print(f"OK: {remote} already has MINDEX_INTERNAL_TOKEN")
                continue
            new_body = merge_env(raw, "MINDEX_INTERNAL_TOKEN", token)
            with sftp.file(remote, "w") as wf:
                wf.write(new_body.encode("utf-8"))
            print(f"OK: wrote MINDEX_INTERNAL_TOKEN to {remote} ({len(new_body)} bytes)")
    finally:
        c187.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
