#!/usr/bin/env python3
"""
Append PETRI_ENGINE_V2_URL to MAS VM 188 orchestrator .env (no sudo) and restart mas-orchestrator.

Uses SFTP-style write via a shell redirect (URL only in remote command — no secrets in argv).
sudo uses stdin password without PTY so the password is not echoed to captured stdout.

Loads VM_PASSWORD / VM_SSH_PASSWORD from .credentials.local (same candidates as deploy_petri_v2_stack_vm187.py).
"""
from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    raise

MAS_ROOT = Path(__file__).resolve().parent.parent
CODE_ROOT = MAS_ROOT.parent.parent

MAS_DOTENV = "/home/mycosoft/mycosoft/mas/.env"


def _load_credentials() -> None:
    loaded = False
    for cand in (
        MAS_ROOT / ".credentials.local",
        CODE_ROOT / "WEBSITE" / "website" / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
    ):
        if not cand.is_file():
            continue
        for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
        loaded = True
        break
    if not loaded:
        sys.exit("No credentials file found for VM SSH")
    if not os.environ.get("VM_PASSWORD") and os.environ.get("VM_SSH_PASSWORD"):
        os.environ["VM_PASSWORD"] = os.environ["VM_SSH_PASSWORD"]


def main() -> None:
    _load_credentials()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        sys.exit("VM_PASSWORD not set")

    petri_url = os.environ.get("PETRI_ENGINE_V2_URL", "http://192.168.0.187:8050").strip().rstrip("/")
    env_line = f"PETRI_ENGINE_V2_URL={petri_url}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=45)

    # 1) Idempotent append (grep pattern avoids leaking credentials in remote argv beyond URL)
    append_cmd = (
        f"grep -q '^PETRI_ENGINE_V2_URL=' {MAS_DOTENV} 2>/dev/null || "
        f"printf '%s\\n' {shlex.quote(env_line)} >> {MAS_DOTENV}"
    )
    stdin, stdout, stderr = client.exec_command(append_cmd, timeout=60)
    stdin.close()
    out_a = stdout.read().decode(errors="replace")
    err_a = stderr.read().decode(errors="replace")
    code_a = stdout.channel.recv_exit_status()
    if code_a != 0:
        client.close()
        print(out_a, err_a, sep="\n", file=sys.stderr)
        sys.exit(code_a)

    # 2) Restart orchestrator — sudo -S without PTY (password not echoed to our pipe reads)
    restart_cmd = "sudo -S systemctl restart mas-orchestrator"
    stdin, stdout, stderr = client.exec_command(restart_cmd, timeout=120)
    stdin.write(pw + "\n")
    stdin.flush()
    stdin.channel.shutdown_write()
    _ = stdout.read()
    err_r = stderr.read().decode(errors="replace")
    code_r = stdout.channel.recv_exit_status()
    client.close()

    if code_r != 0:
        print(err_r, file=sys.stderr)
        sys.exit(code_r)

    # 3) Smoke check (no secrets)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=45)
    stdin, stdout, stderr = client.exec_command(
        "sleep 3 && curl -sS http://127.0.0.1:8001/api/simulation/petri/v2/health",
        timeout=60,
    )
    stdin.close()
    health = stdout.read().decode(errors="replace").strip()
    err_h = stderr.read().decode(errors="replace").strip()
    client.close()
    print(health or "(no body)")
    if err_h:
        print(err_h, file=sys.stderr)
    if not health:
        sys.exit(1)


if __name__ == "__main__":
    main()
