#!/usr/bin/env python3
r"""
Merge CREP transit API keys from local WEBSITE/website/.env.local into
/opt/mycosoft/website/.env on Sandbox 192.168.0.187, then recreate blue/green.

Only copies keys that exist and are non-empty locally. Never prints values.
Keys: see .env.example "CREP Live Transit" section.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

VM = "192.168.0.187"
REMOTE = "/opt/mycosoft/website/.env"
WEBSITE_DIR = "/opt/mycosoft/website"
COMPOSE_FILES = "-f docker-compose.production.yml -f docker-compose.production.blue-green.yml"

TRANSIT_KEYS = (
    "WMATA_API_KEY",
    "WMATA_API_KEY_SECONDARY",
    "TRANSIT_511_API_KEY",
    "BART_API_KEY",
    "MBTA_API_KEY",
    "CTA_TRAIN_TRACKER_API_KEY",
    "CTA_BUS_TRACKER_API_KEY",
    "TRIMET_API_KEY",
    "MARTA_API_KEY",
    "METROLINK_API_KEY",
    "DART_API_KEY",
)


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
    for k, v in updates.items():
        lines_out.append(f"{k}={v}")
    body = "\n".join(lines_out)
    if body and not body.endswith("\n"):
        body += "\n"
    return body


def parse_local_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k, v = k.strip(), v.strip().strip("'\"")
        if k:
            out[k] = v
    return out


def local_env_path() -> Path:
    root = Path(__file__).resolve().parent.parent.parent.parent
    return root / "WEBSITE" / "website" / ".env.local"


def load_creds() -> str:
    root = Path(__file__).resolve().parent.parent
    for p in (root / ".credentials.local", root.parent.parent / "WEBSITE" / "website" / ".credentials.local"):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not pw:
        raise SystemExit("Missing VM_PASSWORD in .credentials.local")
    return pw


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 900) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    local_path = local_env_path()
    local = parse_local_env(local_path)
    updates = {k: local[k] for k in TRANSIT_KEYS if local.get(k)}
    if not updates:
        print(f"No transit keys found in {local_path} — add keys locally, then re-run.")
        return 1
    print(f"Source: {local_path}")
    print(f"Merging {len(updates)} transit key(s) to {REMOTE} (values not shown).")

    pw = load_creds()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM, username="mycosoft", password=pw, timeout=30)
    try:
        sftp = ssh.open_sftp()
        with sftp.open(REMOTE, "r") as rf:
            raw = rf.read().decode("utf-8", errors="replace")
        run(ssh, f'cp -a "{REMOTE}" "{REMOTE}.bak.transit.$(date +%Y%m%d_%H%M%S)"', timeout=60)
        new_body = merge_env_file(raw, updates)
        with sftp.open(REMOTE, "w") as wf:
            wf.write(new_body.encode("utf-8"))
        sftp.close()

        print("Recreating website-blue / website-green …")
        code, o, e = run(
            ssh,
            f"cd {WEBSITE_DIR} && docker compose {COMPOSE_FILES} up -d --no-deps --force-recreate website-green website-blue 2>&1",
            timeout=900,
        )
        print((o + e)[-4000:])
        return 0 if code == 0 else code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
