#!/usr/bin/env python3
"""
Log Docker on Sandbox VM (192.168.0.187) into ghcr.io so `docker pull` works for private images.

Requires in .credentials.local (gitignored):
  GHCR_USERNAME=<GitHub username for the PAT>
  GHCR_PULL_TOKEN=<classic PAT with read:packages, or fine-grained with Packages read>

GitHub CLI tokens (gh auth token) often lack read:packages — use a dedicated PAT for the VM.

Usage:
  python scripts/ghcr_docker_login_sandbox_187.py
  python scripts/ghcr_docker_login_sandbox_187.py --pull ghcr.io/mycosoftlabs/website:production-latest
"""
from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path

import paramiko

SANDBOX = "192.168.0.187"


def load_creds(repo_root: Path) -> tuple[str, str, str]:
    creds = repo_root / ".credentials.local"
    if creds.exists():
        for line in creds.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    user = os.environ.get("VM_SSH_USER", "mycosoft")
    if not pw:
        sys.exit("Missing VM_PASSWORD / VM_SSH_PASSWORD (see .credentials.local)")
    return pw, user, creds


def main() -> None:
    parser = argparse.ArgumentParser(description="GHCR docker login on Sandbox VM 187")
    parser.add_argument(
        "--pull",
        metavar="IMAGE",
        help="After login, run docker pull IMAGE (e.g. ghcr.io/mycosoftlabs/website:production-latest)",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    pw, ssh_user, _creds = load_creds(repo)

    gh_user = os.environ.get("GHCR_USERNAME", "").strip()
    token = os.environ.get("GHCR_PULL_TOKEN", "").strip()
    if not gh_user or not token:
        print(
            "Missing GHCR_USERNAME or GHCR_PULL_TOKEN in environment / .credentials.local.\n"
            "Create a classic PAT: https://github.com/settings/tokens\n"
            "  Required scope: read:packages\n"
            "Add:\n"
            "  GHCR_USERNAME=<your GitHub username>\n"
            "  GHCR_PULL_TOKEN=ghp_...\n"
            "to .credentials.local then re-run.",
            file=sys.stderr,
        )
        sys.exit(1)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SANDBOX, username=ssh_user, password=pw, timeout=90)

    cmd = f"docker login ghcr.io -u {shlex.quote(gh_user)} --password-stdin"
    stdin, stdout, stderr = c.exec_command(cmd)
    stdin.write(token + "\n")
    stdin.flush()
    stdin.channel.shutdown_write()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    print(out.strip())
    if err.strip():
        print(err, file=sys.stderr)
    if code != 0:
        c.close()
        sys.exit(code)

    if args.pull:
        _, stdout, stderr = c.exec_command(f"docker pull {args.pull} 2>&1")
        print(stdout.read().decode(errors="replace"))
        e = stderr.read().decode(errors="replace")
        if e.strip():
            print(e, file=sys.stderr)
        code = stdout.channel.recv_exit_status()
        c.close()
        sys.exit(code)

    c.close()
    print("Login OK. Run on 187: docker pull ghcr.io/mycosoftlabs/website:production-latest")


if __name__ == "__main__":
    main()
